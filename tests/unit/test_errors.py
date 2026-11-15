import json
import logging

from app.core.errors import unhandled_exception_handler
from app.core.logging import ConsoleFormatter, JsonFormatter
from app.main import app
from fastapi.testclient import TestClient
from starlette.requests import Request

_DATABASE_URL = "postgresql://ilka_user:s3cret-pass@db.internal:5432/ilka"


def test_unknown_route_has_error_envelope() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/no-such-route")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "http_error"
    assert "request_id" in body["error"]
    assert "traceback" not in str(body).lower()


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


async def test_unhandled_log_redacts_database_url_and_keeps_diagnostics() -> None:
    capture = _Capture()
    log = logging.getLogger("app.core.errors")
    previous = log.propagate
    log.addHandler(capture)
    log.propagate = False
    log.setLevel(logging.ERROR)
    scope = {
        "type": "http",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/sites",
        "raw_path": b"/api/v1/sites",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("test", 80),
    }
    request = Request(scope)
    request.state.request_id = "req-safe"
    try:
        try:
            raise RuntimeError(f"connect {_DATABASE_URL}")
        except RuntimeError as exc:
            response = await unhandled_exception_handler(request, exc)
    finally:
        log.removeHandler(capture)
        log.propagate = previous
    body = json.loads(response.body)
    rendered = response.body.decode()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An unexpected error occurred"
    assert "s3cret-pass" not in rendered
    assert "ilka_user" not in rendered
    assert len(capture.records) == 1
    record = capture.records[0]
    for line in (JsonFormatter().format(record), ConsoleFormatter().format(record)):
        assert "s3cret-pass" not in line
        assert "ilka_user" not in line
        assert "postgresql://" not in line
        assert "RuntimeError" in line
        assert "req-safe" in line
        assert "/api/v1/sites" in line
        assert "internal_error" in line
        assert "unhandled_error" in line


def test_unhandled_error_is_generic(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/__test/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An unexpected error occurred"
    assert "intentional" not in body["error"]["message"]
