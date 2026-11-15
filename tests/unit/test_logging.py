from __future__ import annotations

import json
import logging
import sys

import pytest
from app.core.logging import ConsoleFormatter, JsonFormatter, _redact, request_id_ctx

_DATABASE_URL = "postgresql+asyncpg://ilka_user:s3cret-pass@db.internal:5432/ilka"
_BEARER = "Bearer eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.sigvalue1"
_RTSP_URL = "rtsp://cam_user:cam-pass@10.0.0.5:554/live"
_API_KEY = "api_key=sk-live-test"


def _record(message: str, *, exc_info: object = None) -> logging.LogRecord:
    record = logging.LogRecord(
        name="ilka.errors",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=exc_info,
    )
    record.request_id = "req-safe"  # type: ignore[attr-defined]
    record.method = "GET"  # type: ignore[attr-defined]
    record.path = "/api/v1/sites"  # type: ignore[attr-defined]
    record.error_code = "internal_error"  # type: ignore[attr-defined]
    record.exception_type = "RuntimeError"  # type: ignore[attr-defined]
    return record


def _rendered(record: logging.LogRecord) -> tuple[str, str]:
    return JsonFormatter().format(record), ConsoleFormatter().format(record)


def test_redact_hides_secret_keys() -> None:
    payload = _redact({"password": "hunter2", "ok": "visible", "DATABASE_URL": "postgresql://x"})
    assert payload["password"] == "***"
    assert payload["ok"] == "visible"
    assert payload["DATABASE_URL"] == "***"


def test_json_log_includes_request_id_from_context() -> None:
    token = request_id_ctx.set("req-123")
    try:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        record.taskName = "should-not-appear"  # type: ignore[attr-defined]
        line = JsonFormatter().format(record)
        payload = json.loads(line)
        assert payload["request_id"] == "req-123"
        assert "taskName" not in payload.get("context", {})
        assert "should-not-appear" not in line
    finally:
        request_id_ctx.reset(token)


def test_stable_error_code_is_not_treated_as_a_token() -> None:
    json_line, console_line = _rendered(_record("oidc_token_rejected"))
    assert "oidc_token_rejected" in json_line
    assert "oidc_token_rejected" in console_line


@pytest.mark.parametrize("line_at", [0, 1])
def test_database_url_and_bearer_token_are_redacted(line_at: int) -> None:
    message = f"connect failed {_DATABASE_URL} auth {_BEARER} {_RTSP_URL} {_API_KEY}"
    json_line, console_line = _rendered(_record(message))
    line = (json_line, console_line)[line_at]
    assert "s3cret-pass" not in line
    assert "ilka_user" not in line
    assert "sigvalue1" not in line
    assert "cam-pass" not in line
    assert "sk-live-test" not in line
    assert "postgresql+asyncpg://" not in line
    assert "rtsp://" not in line
    assert "internal_error" in line
    assert "req-safe" in line
    assert "/api/v1/sites" in line


def test_traceback_redacts_secrets_and_keeps_exception_class() -> None:
    try:
        raise RuntimeError(f"database {_DATABASE_URL} {_BEARER}")
    except RuntimeError:
        record = _record("unhandled_error", exc_info=sys.exc_info())
    json_line, console_line = _rendered(record)
    payload = json.loads(json_line)
    for line in (json_line, console_line):
        assert "s3cret-pass" not in line
        assert "ilka_user" not in line
        assert "sigvalue1" not in line
        assert "RuntimeError" in line
        assert "req-safe" in line
        assert "/api/v1/sites" in line
        assert "internal_error" in line
        assert "unhandled_error" in line
    assert payload["exception_type"] == "RuntimeError"
    assert payload["context"]["error_code"] == "internal_error"
    assert payload["context"]["path"] == "/api/v1/sites"
    assert payload["request_id"] == "req-safe"
    assert "Traceback" in payload["error"]
    assert "Traceback" in console_line


def test_console_formatter_includes_level_and_logger() -> None:
    record = logging.LogRecord(
        name="ilka",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Application started",
        args=(),
        exc_info=None,
    )
    line = ConsoleFormatter().format(record)
    assert "INFO" in line
    assert "ilka" in line
    assert "Application started" in line
