import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app, create_app


def test_health_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert response.headers.get("x-request-id")


def test_health_ok_without_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("ILKA_POSTGRES_URL", "")
    get_settings.cache_clear()
    application = create_app()
    with TestClient(application) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    get_settings.cache_clear()


def test_ready_ok_with_sqlite() -> None:
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"


def test_api_v1_status() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json()["api"] == "v1"


def test_status_operational() -> None:
    with TestClient(app) as client:
        response = client.get("/status")
    assert response.status_code == 200
    body = response.json()
    assert body["application"] == "ILKA"
    assert body["environment"] == "testing"
    assert body["status"] == "operational"
    joined = " ".join(str(value).lower() for value in body.values())
    assert "password" not in joined
    assert "postgresql" not in joined
    assert "token" not in joined


def test_docs_and_redoc_are_available() -> None:
    with TestClient(app) as client:
        docs = client.get("/docs")
        redoc = client.get("/redoc")
        openapi = client.get("/openapi.json")
    assert docs.status_code == 200
    assert redoc.status_code == 200
    assert openapi.status_code == 200
    assert "ILKA" in openapi.json()["info"]["title"]
