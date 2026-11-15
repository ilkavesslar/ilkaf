"""Health API tests for pytest run from the backend directory."""

from app.main import app
from fastapi.testclient import TestClient


def test_health_returns_healthy() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
