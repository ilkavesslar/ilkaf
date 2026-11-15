# Docker static review (Sprint 0.5)

Docker CLI was **not** available to run Compose in this environment. Review is **static** only.

## `backend/Dockerfile`

- Base: `python:3.11-slim` (reasonable).
- Copies `app`, `alembic`, `pyproject.toml`, `alembic.ini`.
- Installs the package; runs `uvicorn app.main:app`.
- Does **not** auto-apply migrations (safer; operator runs `alembic upgrade head`).
- Does **not** bake `.env` or credentials.

## `compose.yaml`

- `postgres:16-alpine` with local user `ilka` / password `ilka_dev_only` / db `ilka`.
- Healthcheck `pg_isready`.
- Backend `DATABASE_URL` points at service hostname `postgres`.
- No Redis (ADR 0006).
- Named volume `ilka_pgdata` — local only.

## Residual risk

Images and network isolation are unverified until Docker Desktop (or equivalent) is installed and `docker compose up` is run by a human.
