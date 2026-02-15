from __future__ import annotations

import json

import pytest
from google.genai.errors import ServerError

from app import create_app
from extensions import db
from models import ChatMessage, ChatSession, User


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
        user = User(username="tester", email="tester@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    csrf_token = get_csrf_token(client)
    return client.post(
        "/api/auth/login",
        json={"username": "tester", "password": "password123"},
        headers={"X-CSRFToken": csrf_token},
    )


def get_csrf_token(client):
    response = client.get("/api/csrf")
    payload = json.loads(response.data)
    return payload["csrf_token"]


def test_chat_page_creates_session(client, app):
    login(client)
    response = client.get("/api/chat/sessions")
    assert response.status_code == 200

    with app.app_context():
        sessions = ChatSession.query.all()
        assert len(sessions) == 1
        assert sessions[0].title


def test_index_page_loads_for_logged_in_user(client):
    login(client)
    response = client.get("/")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "static/spa/app.js" in page
    assert 'id="imageViewerModal"' in page
    assert 'id="roughUploadPreviewImage"' in page
    assert 'id="referenceRoughPreviewImage"' in page


def test_text_chat_persists_messages(client, app, monkeypatch):
    login(client)

    with app.app_context():
        session = ChatSession(user_id=User.query.first().id, title="新しいチャット")
        db.session.add(session)
        db.session.commit()
        session_id = session.id

    monkeypatch.setattr("services.chat_service.generate_multimodal_reply", lambda *_: "test reply")

    response = client.post(
        f"/api/chat/sessions/{session_id}/messages",
        data={"mode_id": "text_chat", "message": "こんにちは"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload["assistant"]["text"] == "test reply"

    with app.app_context():
        messages = (
            ChatMessage.query.filter_by(session_id=session_id)
            .order_by(ChatMessage.id.asc())
            .all()
        )
        assert len(messages) == 2
        roles = [message.role for message in messages]
        assert roles == ["user", "assistant"]


def test_text_chat_accepts_json_payload(client, app, monkeypatch):
    login(client)

    with app.app_context():
        session = ChatSession(user_id=User.query.first().id, title="新しいチャット")
        db.session.add(session)
        db.session.commit()
        session_id = session.id

    monkeypatch.setattr("services.chat_service.generate_multimodal_reply", lambda *_: "json reply")

    response = client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={"message": "JSON送信"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload["assistant"]["text"] == "json reply"


def test_text_chat_returns_503_when_gemini_is_overloaded(client, app, monkeypatch):
    login(client)

    with app.app_context():
        session = ChatSession(user_id=User.query.first().id, title="新しいチャット")
        db.session.add(session)
        db.session.commit()
        session_id = session.id

    overloaded_error = ServerError(
        503,
        {
            "error": {
                "code": 503,
                "message": "The model is overloaded. Please try again later.",
                "status": "UNAVAILABLE",
            }
        },
        None,
    )

    def fake_generate_reply(*args, **kwargs):
        raise overloaded_error

    monkeypatch.setattr("services.chat_service.generate_multimodal_reply", fake_generate_reply)

    response = client.post(
        f"/api/chat/sessions/{session_id}/messages",
        data={"mode_id": "text_chat", "message": "テスト"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 503
    payload = json.loads(response.data)
    assert payload["error"] == "現在Geminiが混み合っています。少し時間をおいてから再試行してください。"
    assert payload["error_code"] == "gemini_overloaded"


def test_text_chat_returns_500_with_contact_message_for_unexpected_error(client, app, monkeypatch):
    login(client)

    with app.app_context():
        session = ChatSession(user_id=User.query.first().id, title="新しいチャット")
        db.session.add(session)
        db.session.commit()
        session_id = session.id

    def fake_generate_reply(*args, **kwargs):
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr("services.chat_service.generate_multimodal_reply", fake_generate_reply)

    response = client.post(
        f"/api/chat/sessions/{session_id}/messages",
        data={"mode_id": "text_chat", "message": "テスト"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 500
    payload = json.loads(response.data)
    assert payload["error"] == "システムエラーが発生しました。管理者にお問い合わせください。"
    assert payload["error_code"] == "internal_server_error_contact_admin"
