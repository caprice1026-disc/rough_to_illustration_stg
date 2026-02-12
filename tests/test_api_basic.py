from __future__ import annotations

import json
from io import BytesIO

import pytest
from google.genai.errors import ServerError
from PIL import Image

from app import create_app
from extensions import db
from illust import GeneratedImage
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
        user = User(username="tester", email="tester@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def get_csrf_token(client):
    response = client.get("/api/csrf")
    payload = json.loads(response.data)
    return payload["csrf_token"]


def login(client):
    csrf_token = get_csrf_token(client)
    return client.post(
        "/api/auth/login",
        json={"username": "tester", "password": "password123"},
        headers={"X-CSRFToken": csrf_token},
    )


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload["status"] == "ok"


def test_generation_flow_creates_asset(client, monkeypatch):
    login(client)

    image = Image.new("RGB", (4, 4), (255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    raw_bytes = buffer.getvalue()

    def fake_generate_image(*args, **kwargs):
        return GeneratedImage(image=image, raw_bytes=raw_bytes, mime_type="image/png", prompt="test")

    monkeypatch.setattr("services.generation_service.generate_image", fake_generate_image)

    csrf_token = get_csrf_token(client)
    response = client.post(
        "/api/generations",
        data={
            "mode": "rough_with_instructions",
            "color_instruction": "red",
            "pose_instruction": "pose",
            "aspect_ratio": "auto",
            "resolution": "auto",
            "rough_image": (BytesIO(raw_bytes), "rough.png"),
        },
        headers={"X-CSRFToken": csrf_token},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload["generation"]["status"] == "succeeded"
    assert payload["assets"]
    assert payload["assets"][0]["url"]


def test_generation_returns_503_when_gemini_is_overloaded(client, monkeypatch):
    login(client)

    image = Image.new("RGB", (4, 4), (255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    raw_bytes = buffer.getvalue()

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

    def fake_run_generation_rough(**kwargs):
        raise overloaded_error

    monkeypatch.setattr("services.generation_service.run_generation_rough", fake_run_generation_rough)

    csrf_token = get_csrf_token(client)
    response = client.post(
        "/api/generations",
        data={
            "mode": "rough_with_instructions",
            "color_instruction": "red",
            "pose_instruction": "pose",
            "aspect_ratio": "auto",
            "resolution": "auto",
            "rough_image": (BytesIO(raw_bytes), "rough.png"),
        },
        headers={"X-CSRFToken": csrf_token},
        content_type="multipart/form-data",
    )
    assert response.status_code == 503
    payload = json.loads(response.data)
    assert payload["error"] == "現在Geminiが混み合っています。少し時間をおいてから再試行してください。"
    assert payload["error_code"] == "gemini_overloaded"


def test_generation_returns_500_with_contact_message_for_unexpected_error(client, monkeypatch):
    login(client)

    image = Image.new("RGB", (4, 4), (255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    raw_bytes = buffer.getvalue()

    def fake_run_generation_rough(**kwargs):
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr("services.generation_service.run_generation_rough", fake_run_generation_rough)

    csrf_token = get_csrf_token(client)
    response = client.post(
        "/api/generations",
        data={
            "mode": "rough_with_instructions",
            "color_instruction": "red",
            "pose_instruction": "pose",
            "aspect_ratio": "auto",
            "resolution": "auto",
            "rough_image": (BytesIO(raw_bytes), "rough.png"),
        },
        headers={"X-CSRFToken": csrf_token},
        content_type="multipart/form-data",
    )
    assert response.status_code == 500
    payload = json.loads(response.data)
    assert payload["error"] == "システムエラーが発生しました。管理者にお問い合わせください。"
    assert payload["error_code"] == "internal_server_error_contact_admin"
