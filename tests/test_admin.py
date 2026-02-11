from __future__ import annotations

import json

import pytest

from app import create_app
from extensions import db
from models import User


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
            "APP_AUTO_MIGRATE": False,
            "APP_AUTO_INIT_USER": False,
        }
    )
    with app.app_context():
        db.create_all()
        admin = User(username="admin", email="admin@example.com")
        admin.set_password("password123")
        admin.role = "admin"
        db.session.add(admin)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def get_csrf_token(client):
    response = client.get("/api/csrf")
    payload = json.loads(response.data)
    return payload["csrf_token"]


def login_admin(client):
    return login_user(client, "admin", "password123")


def login_user(client, username: str, password: str):
    csrf_token = get_csrf_token(client)
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRFToken": csrf_token},
    )


def test_admin_can_create_user(client, app):
    login_admin(client)
    response = client.post(
        "/api/admin/users",
        json={"username": "member", "email": "member@example.com", "password": "pass1234"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 201
    payload = json.loads(response.data)
    assert payload["user"]["username"] == "member"

    with app.app_context():
        created = User.query.filter_by(username="member").first()
        assert created is not None
        assert created.is_active is True


def test_inactive_user_cannot_login(client, app):
    with app.app_context():
        user = User(username="inactive", email="inactive@example.com")
        user.set_password("password123")
        user.is_active = False
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/api/auth/login",
        json={"username": "inactive", "password": "password123"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 403


def test_user_can_change_own_password(client, app):
    with app.app_context():
        user = User(username="member", email="member@example.com")
        user.set_password("old-password")
        db.session.add(user)
        db.session.commit()

    login_user(client, "member", "old-password")
    response = client.patch(
        "/api/users/me/password",
        json={"current_password": "old-password", "new_password": "new-password"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload["ok"] is True

    logout_response = client.post("/api/auth/logout", headers={"X-CSRFToken": get_csrf_token(client)})
    assert logout_response.status_code == 200

    old_login_response = login_user(client, "member", "old-password")
    assert old_login_response.status_code == 401

    new_login_response = login_user(client, "member", "new-password")
    assert new_login_response.status_code == 200


def test_change_own_password_requires_current_password_match(client, app):
    with app.app_context():
        user = User(username="member", email="member@example.com")
        user.set_password("old-password")
        db.session.add(user)
        db.session.commit()

    login_user(client, "member", "old-password")
    response = client.patch(
        "/api/users/me/password",
        json={"current_password": "invalid", "new_password": "new-password"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 400


def test_admin_can_change_own_password(client):
    login_admin(client)
    response = client.patch(
        "/api/users/me/password",
        json={"current_password": "password123", "new_password": "admin-password-2"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 200

    logout_response = client.post("/api/auth/logout", headers={"X-CSRFToken": get_csrf_token(client)})
    assert logout_response.status_code == 200

    old_login_response = login_user(client, "admin", "password123")
    assert old_login_response.status_code == 401

    new_login_response = login_user(client, "admin", "admin-password-2")
    assert new_login_response.status_code == 200


def test_admin_can_promote_user_to_admin(client, app):
    with app.app_context():
        user = User(username="member", email="member@example.com")
        user.set_password("member-password")
        user.role = "user"
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    login_admin(client)
    response = client.patch(
        f"/api/admin/users/{user_id}/role",
        json={"role": "admin"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload["user"]["role"] == "admin"

    with app.app_context():
        promoted = User.query.filter_by(id=user_id).first()
        assert promoted is not None
        assert promoted.role == "admin"


def test_admin_cannot_reset_own_password_via_admin_endpoint(client, app):
    with app.app_context():
        admin = User.query.filter_by(username="admin").first()
        assert admin is not None
        admin_id = admin.id

    login_admin(client)
    response = client.patch(
        f"/api/admin/users/{admin_id}/password",
        json={"password": "new-password"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 400


def test_non_admin_cannot_promote_user(client, app):
    with app.app_context():
        operator = User(username="operator", email="operator@example.com")
        operator.set_password("operator-password")
        operator.role = "user"
        target = User(username="target", email="target@example.com")
        target.set_password("target-password")
        target.role = "user"
        db.session.add(operator)
        db.session.add(target)
        db.session.commit()
        target_id = target.id

    login_user(client, "operator", "operator-password")
    response = client.patch(
        f"/api/admin/users/{target_id}/role",
        json={"role": "admin"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 403
