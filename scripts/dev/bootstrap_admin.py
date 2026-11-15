"""Prompt for the first SYSTEM_ADMIN. Password is not echoed or stored in argv."""

from __future__ import annotations

import asyncio
import getpass
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.core.db import configure_database, session_scope  # noqa: E402
from app.services.bootstrap_admin import (  # noqa: E402
    BootstrapError,
    provision_first_admin,
    session_cookie_attributes,
)


def _target() -> str:
    settings = get_settings()
    url = settings.resolved_database_url
    if not url:
        return ""
    parsed = urlparse(url.replace("+asyncpg", "").replace("+psycopg", ""))
    scheme = (parsed.scheme or "").split("+")[0]
    name = (parsed.path or "").lstrip("/")
    return f"{scheme} host={parsed.hostname or ''} name={name}"


def _read_credentials() -> tuple[str, str]:
    email = input("Admin email: ").strip()
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise BootstrapError("Passwords do not match")
    return email, password


async def _provision(email: str, password: str) -> tuple[str, str]:
    settings = get_settings()
    if configure_database(settings) is None:
        raise BootstrapError("No database is configured")
    async with session_scope() as session:
        return await provision_first_admin(session, email, password)


def _verify_login(email: str, password: str) -> bool:
    import httpx

    try:
        with httpx.Client(base_url="http://127.0.0.1:8000", timeout=15) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            attributes = session_cookie_attributes(login.headers.get("set-cookie", ""))
            me = client.get("/api/v1/auth/me")
            body = me.json() if me.status_code == 200 else {}
            logout = client.post("/api/v1/auth/logout", json={})
            again = client.get("/api/v1/auth/me")
    except httpx.HTTPError:
        print("Login check could not reach http://127.0.0.1:8000.", file=sys.stderr)
        return False
    lowered = [item.lower() for item in attributes]
    cookie_ok = (
        any(item == "httponly" for item in lowered)
        and any(item == "samesite=lax" for item in lowered)
        and not any(item == "secure" for item in lowered)
    )
    print("login", login.status_code)
    print("cookie", "; ".join(attributes) if attributes else "missing")
    print(
        "me",
        me.status_code,
        "role_ok",
        body.get("roles") == ["SYSTEM_ADMIN"],
        "email_ok",
        body.get("email") == email,
    )
    print("logout", logout.status_code)
    print("me_after_logout", again.status_code)
    return (
        login.status_code == 200
        and cookie_ok
        and me.status_code == 200
        and body.get("roles") == ["SYSTEM_ADMIN"]
        and body.get("email") == email
        and logout.status_code == 200
        and again.status_code == 401
    )


def main() -> int:
    if not sys.stdin.isatty():
        print(
            "Run this in a terminal so the password stays hidden.",
            file=sys.stderr,
        )
        print(f"{sys.executable} {Path(__file__)}", file=sys.stderr)
        return 2
    target = _target()
    if not target:
        print("No database is configured.", file=sys.stderr)
        return 1
    print(f"Database: {target}")
    print("Creates the first SYSTEM_ADMIN. Refuses when one already exists.")
    try:
        email, password = _read_credentials()
        stored_email, organization = asyncio.run(_provision(email, password))
    except BootstrapError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 1
    print(f"SYSTEM_ADMIN created for {stored_email} in organization {organization}.")
    if not _verify_login(stored_email, password):
        print("Account exists. Login check did not pass.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
