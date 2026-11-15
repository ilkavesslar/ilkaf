from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_SECRET_KEYS = re.compile(
    r"(password|secret|token|authorization|api[_-]?key|dsn|database_url|ilka_postgres|rtsp)",
    re.IGNORECASE,
)

# Database, cache, broker, and camera URLs. https links without userinfo stay so
# library error references are not erased.
_SECRET_URL = re.compile(
    r"(?i)\b(?:"
    r"(?:postgres(?:ql)?|mysql|mariadb|mongodb|redis|rediss|amqp|amqps|rtsp|rtsps)"
    r"(?:\+[a-z0-9]+)?://[^\s'\"<>)]+"
    r"|[a-z][a-z0-9+.-]*://[^\s/:@'\"<>)]+(?::[^\s/@'\"<>)]*)?@[^\s'\"<>)]+"
    r")"
)
_BEARER = re.compile(r"(?i)\b(Bearer\s+)[A-Za-z0-9\-._~+/]+=*")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
_SECRET_ASSIGN = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|client[_-]?secret|api[_-]?key|access[_-]?key|"
    r"refresh[_-]?token|id[_-]?token|access[_-]?token|database[_-]?url|dsn|token)"
    r"\s*([:=])\s*(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s&'\"]+)"
)

request_id_ctx: ContextVar[str | None] = ContextVar("ilka_request_id", default=None)

_ALLOWED_CONTEXT = frozenset(
    {
        "method",
        "path",
        "status_code",
        "duration_ms",
        "error_code",
        "exception_type",
    }
)


def redact_text(value: str) -> str:
    """Remove credential-shaped text. Stable words such as error codes stay."""
    redacted = _SECRET_URL.sub("***", value)
    redacted = _BEARER.sub(r"\1***", redacted)
    redacted = _JWT.sub("***", redacted)
    return _SECRET_ASSIGN.sub(lambda match: f"{match.group(1)}{match.group(2)}***", redacted)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if _SECRET_KEYS.search(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        if _SECRET_KEYS.search(value):
            return "***"
        return redact_text(value)
    return value


def _request_id(record: logging.LogRecord) -> str | None:
    request_id = getattr(record, "request_id", None) or request_id_ctx.get()
    if request_id is None:
        return None
    return str(request_id)


def _exception_type_name(record: logging.LogRecord) -> str | None:
    if record.exc_info and record.exc_info[0] is not None:
        return record.exc_info[0].__name__
    recorded = record.__dict__.get("exception_type")
    if isinstance(recorded, str) and recorded:
        return recorded
    return None


def _redacted_traceback(formatter: logging.Formatter, record: logging.LogRecord) -> str | None:
    if not record.exc_info or record.exc_info[0] is None:
        return None
    return redact_text(formatter.formatException(record.exc_info))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", "ilka-backend"),
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        request_id = _request_id(record)
        if request_id:
            payload["request_id"] = request_id
        exception_type = _exception_type_name(record)
        if exception_type:
            payload["exception_type"] = exception_type
        traceback_text = _redacted_traceback(self, record)
        if traceback_text:
            payload["error"] = traceback_text
        extra = {
            key: value for key, value in record.__dict__.items() if key in _ALLOWED_CONTEXT
        }
        if extra:
            payload["context"] = _redact(extra)
        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console logs for local development."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        parts = [timestamp, record.levelname, record.name, redact_text(record.getMessage())]
        request_id = _request_id(record)
        if request_id:
            parts.append(f"request_id={request_id}")
        exception_type = _exception_type_name(record)
        if exception_type:
            parts.append(f"exception_type={exception_type}")
        for key in ("method", "path", "status_code", "duration_ms", "error_code"):
            if key in record.__dict__:
                parts.append(f"{key}={redact_text(str(record.__dict__[key]))}")
        line = " ".join(parts)
        traceback_text = _redacted_traceback(self, record)
        if traceback_text:
            return f"{line}\n{traceback_text}"
        return line


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()  # type: ignore[attr-defined]
        return True


def configure_logging(level: str, service_name: str, *, json_logs: bool = True) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if json_logs else ConsoleFormatter())

    class ServiceFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.service = service_name  # type: ignore[attr-defined]
            return True

    handler.addFilter(ServiceFilter())
    handler.addFilter(RequestIdFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
