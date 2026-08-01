import bcrypt
from fastapi.testclient import TestClient

from app.api import routes_auth
from app.main import app

client = TestClient(app)


def _configure_auth(monkeypatch):
    password_hash = bcrypt.hashpw(
        b"test-password",
        bcrypt.gensalt(),
    ).decode()

    monkeypatch.setattr(
        routes_auth.settings,
        "jwt_secret_key",
        "test-secret-key",
    )
    monkeypatch.setattr(
        routes_auth.settings,
        "auth_username",
        "admin",
    )
    monkeypatch.setattr(
        routes_auth.settings,
        "auth_password_hash",
        password_hash,
    )


def test_login_success(monkeypatch):
    _configure_auth(monkeypatch)

    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "test-password",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(monkeypatch):
    _configure_auth(monkeypatch)

    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401


def test_login_wrong_username(monkeypatch):
    _configure_auth(monkeypatch)

    response = client.post(
        "/api/auth/login",
        json={
            "username": "wrong-user",
            "password": "test-password",
        },
    )

    assert response.status_code == 401


def test_login_not_configured(monkeypatch):
    monkeypatch.setattr(
        routes_auth.settings,
        "jwt_secret_key",
        "",
    )
    monkeypatch.setattr(
        routes_auth.settings,
        "auth_password_hash",
        "",
    )

    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "test-password",
        },
    )

    assert response.status_code == 503
