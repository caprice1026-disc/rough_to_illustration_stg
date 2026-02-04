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
    csrf_token = get_csrf_token(client)
    return client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "password123"},
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
