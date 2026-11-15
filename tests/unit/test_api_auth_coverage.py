"""OpenAPI-driven check that /api routes require authentication unless allowlisted."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

# Intentionally public API operations. Adding a new /api route without auth
# must either include it here (with review) or fail this test.
_PUBLIC_API_OPERATIONS = frozenset(
    {
        ("/api/v1/status", "get"),
        ("/api/v1/auth/login", "post"),
        ("/api/v1/auth/logout", "post"),
    }
)


def test_openapi_api_routes_require_authentication() -> None:
    with TestClient(app) as client:
        spec = client.get("/openapi.json").json()
        paths = spec.get("paths") or {}
        checked = 0
        for path, operations in paths.items():
            if not path.startswith("/api"):
                continue
            for method, _operation in operations.items():
                if method.startswith("x-") or method == "parameters":
                    continue
                method_l = method.lower()
                if method_l == "options":
                    continue
                if (path, method_l) in _PUBLIC_API_OPERATIONS:
                    public = client.request(method_l.upper(), _fill_path(path))
                    assert public.status_code != 401, path
                    continue
                url = _fill_path(path)
                kwargs: dict = {}
                if method_l in {"post", "put", "patch"}:
                    kwargs["json"] = {}
                response = client.request(method_l.upper(), url, **kwargs)
                assert response.status_code == 401, (
                    f"{method_l.upper()} {path} returned {response.status_code}; "
                    "protected API routes must authenticate"
                )
                checked += 1
        assert checked >= 8
        status = client.get("/api/v1/status")
        assert status.status_code == 200


def _fill_path(path: str) -> str:
    sample = str(uuid4())
    return (
        path.replace("{site_id}", sample)
        .replace("{camera_id}", sample)
        .replace("{user_id}", sample)
    )
