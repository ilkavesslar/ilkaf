from fastapi.testclient import TestClient

from app.core.auth_boundary import mutation_requires_authentication
from app.main import app


def test_mutation_gate_matches_api_prefix() -> None:
    assert mutation_requires_authentication("POST", "/api/v1/sites")
    assert mutation_requires_authentication("PUT", "/api/v1/me")
    assert mutation_requires_authentication("PATCH", "/api/anything")
    assert mutation_requires_authentication("DELETE", "/api/v1/x")
    assert not mutation_requires_authentication("GET", "/api/v1/me")
    assert not mutation_requires_authentication("OPTIONS", "/api/v1/me")
    assert not mutation_requires_authentication("POST", "/health")


def test_mutating_api_is_401_without_login() -> None:
    with TestClient(app) as client:
        post = client.post("/api/v1/sites", json={"name": "x", "code": "XX"})
        assert post.status_code == 401
        patch = client.patch(
            "/api/v1/sites/00000000-0000-0000-0000-000000000001",
            json={"name": "x"},
        )
        assert patch.status_code == 401
        body = post.json()
        assert body["error"]["code"] == "http_error"


def test_authorization_header_is_not_trusted() -> None:
    headers = {"Authorization": "Bearer not-a-real-token"}
    with TestClient(app) as client:
        me = client.get("/api/v1/me", headers=headers)
        assert me.status_code == 401
        created = client.post("/api/v1/sites", headers=headers, json={"name": "x", "code": "XX"})
        assert created.status_code == 401


def test_public_gets_remain_available() -> None:
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/status").status_code == 200


def test_unauthenticated_site_get_is_401() -> None:
    with TestClient(app) as client:
        listed = client.get("/api/v1/sites")
        assert listed.status_code == 401
        alias = client.get("/api/sites")
        assert alias.status_code == 401
