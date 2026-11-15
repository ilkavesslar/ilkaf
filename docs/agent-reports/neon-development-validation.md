# Neon development validation

**Date:** 2026-08-21  
**Branch:** `feature/sprint-0-foundation`  
**Status:** **NEON VALIDATION PASS**

Do not start Sprint 1 (cameras / RTSP / CV / AI).

## Environment

- Provider: Neon
- Environment: development
- PostgreSQL: 18
- Region: Singapore
- Neon Auth: disabled
- Authentication architecture: ADR 0010

## Configuration

- ILKA_POSTGRES_URL configured: YES
- Secret committed: NO

Canonical runtime variable remains `DATABASE_URL`. `ILKA_POSTGRES_URL` is the Neon / CI / Compose gate and development fallback when `DATABASE_URL` is empty. The connection string lives only in gitignored `.env`.

## Migration

- Starting revision: empty (no `alembic_version` row)
- Migrations applied: `0001_foundation`, `0002_auth_prep`
- Final revision: `0002_auth_prep` (head)
- Result: success

No `DROP DATABASE` / `DROP SCHEMA` / `TRUNCATE` was issued as an operational command. Existing integration tests include Alembic upgrade/downgrade/upgrade against the development database.

## PostgreSQL Integration

- Tests executed: 3
- Passed: 3
- Failed: 0
- Skipped: 0

Covered: connection, SQLAlchemy CRUD/constraints, Alembic compatibility, `/ready`.

## Backend

- `/health`: HTTP 200, `x-request-id` present, no credential in body
- `/ready`: HTTP 200, database ok, no credential in body
- 404 error envelope includes `request_id`, no credential in body

## Full Tests

- pytest: **24 passed** (unit + integration)
- ruff: pass
- frontend tests: **4 passed**
- frontend build: pass

## Docker

Docker CLI is not installed on this workstation. Environment limitation, not a code failure. Neon was not replaced with local Compose Postgres.

## Security

- `.env` ignored (`git check-ignore .env` → `.env`)
- credential not committed
- credential not logged in health/ready/error bodies
- Helpers redact connection strings in Alembic runner output

**Operational note:** a development database password was pasted into chat (and briefly into source by accident, then removed). Rotate the Neon role password in the Neon console. Do not paste secrets into chat again.

## Remaining Issues

- Docker Compose runtime validation still unavailable until Docker is installed.
- Rotate the exposed development database password.
