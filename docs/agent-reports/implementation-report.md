# Sprint 0.5 implementation report

**Agent:** Builder (Cursor)  
**Date:** 2026-08-20  
**Branch intent:** `feature/sprint-0-foundation` (git identity may still block commits)

## What changed

- ADR 0010: hybrid OIDC + ILKA authorization records. No login API.
- `Principal`, permission and org/site helpers; `GET /api/v1/me` returns 401.
- Users: nullable unique `idp_subject`; indexes on `users.organization_id` and `sites.organization_id` (Alembic `0002_auth_prep`).
- Request-id `ContextVar` on JSON logs; request access log (method/path/status/duration only). Extra log fields allow-listed.
- `/__test/boom` remains testing-only (covered for development 404).
- CI: `backend-postgres` job with Postgres 16; unit tests stay SQLite.
- Frontend `src/services/api.ts` + offline tests; `SystemStatus` uses it.

## Not done

OIDC IdP, password login, Neon live `/ready`, Docker Compose execution, GitHub Actions on a remote, git commits if author identity is unset.

## Tests expected locally

`pytest tests/unit`; `pytest tests/integration` skips without `ILKA_POSTGRES_URL`; `npm test` / `npm run build` in `frontend/`.
