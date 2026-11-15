# Sprint 0.5 architecture plan

**Agent:** Architect  
**Date:** 2026-08-20  
**Do not start Sprint 1 (cameras).**

## Preserve

Working FastAPI health/ready, SQLAlchemy/Alembic identity tables, Vite shell, SQLite unit tests, Compose/CI files, secret gitignore.

## Decisions this sprint

1. **Authentication (ADR 0010):** Hybrid — OIDC for identity; ILKA owns users/orgs/sites/roles. **No login implementation.**
2. **RBAC:** Document scopes + reusable `Principal` helpers. Protected routes return 401 until IdP exists. No hardcoded users.
3. **Postgres:** CI Postgres service + optional `ILKA_POSTGRES_URL`. SQLite remains unit-test only.
4. **Security:** Request-id on logs; boom route only in `testing`; no secret leaks.

## Out of scope

RTSP, CV, incidents, Redis, real OIDC server, password login.
