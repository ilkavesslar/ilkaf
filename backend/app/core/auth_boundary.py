"""Historical fail-closed gate from Sprint 0.5.

Mutating `/api/` routes now use OIDC bearer validation (`app.core.security`).
This module remains only as a helper for tests that still describe the old
prefix-matching behavior.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.errors import error_body

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_API_PREFIX = "/api/"


def mutation_requires_authentication(method: str, path: str) -> bool:
    if method.upper() not in MUTATING_METHODS:
        return False
    return path.startswith(_API_PREFIX)


def unauthenticated_mutation_response(request: Request) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=401,
        content=error_body("http_error", "Authentication required", request_id),
        headers={"x-request-id": request_id} if request_id else {},
    )
