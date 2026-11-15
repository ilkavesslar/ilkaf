from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def error_body(code: str, message: str, request_id: str | None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body("http_error", str(exc.detail), request_id),
    )


def _error_context(
    request: Request, request_id: str | None, code: str, exc: Exception
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "error_code": code,
        "exception_type": type(exc).__name__,
    }


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.info(
        "validation_error",
        extra=_error_context(request, request_id, "validation_error", exc),
    )
    return JSONResponse(
        status_code=422,
        content=error_body("validation_error", "Request validation failed", request_id),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    # Log the class, route, and stable code. The formatter redacts traceback text.
    logger.error(
        "unhandled_error",
        extra=_error_context(request, request_id, "internal_error", exc),
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    # Never return stack traces or exception text to API clients.
    return JSONResponse(
        status_code=500,
        content=error_body("internal_error", "An unexpected error occurred", request_id),
    )
