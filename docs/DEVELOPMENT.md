# Local development (Sprint 2 identity + Sprint 1 foundation)

The Python virtual environment lives at the **repository root** (`.venv`), not inside `backend/`. Use the same location in every command below.

Python 3.11+ and Node 22+ (or 20+). Docker is **optional**. PostgreSQL is required for `/ready` and Alembic against a real database; `/health` and `/status` work without it.

## 1. Clone the repository

```powershell
git clone <repository-url>
cd ilka
```

For the daily three-terminal workflow on this Intel Mac (backend / frontend / `.venv-cv`), see [`development/startup.md`](./development/startup.md).

## 2. Create the virtual environment

```powershell
python -m venv .venv
```

## 3. Activate the virtual environment

```powershell
.venv\Scripts\Activate.ps1
```

## 4. Install requirements

```powershell
python -m pip install --upgrade pip
pip install -e "./backend[dev]"
```

Equivalent from `backend/`: `pip install -r requirements.txt` then install pytest extras if you did not use `.[dev]`.

```powershell
cd frontend
npm install
cd ..
```

## 5. Create `.env`

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`. A shorter backend copy exists at `backend/.env.example`; the repo-root file is canonical.

## 6. Configure the database

Set `DATABASE_URL` (canonical) or `ILKA_POSTGRES_URL` (Neon / local Compose fallback) in `.env`. Placeholder example (not a real secret):

```text
DATABASE_URL=postgresql://ilka_user:password@localhost:5432/ilka
```

The running app converts `postgresql://` to SQLAlchemy `postgresql+asyncpg://`. Optional Compose: `docker compose up postgres` then use `postgresql+asyncpg://ilka:ilka_dev_only@localhost:5432/ilka`.

Production startup requires `DATABASE_URL` by name. Never put the real connection string in git, chat, or `.env.example`.

## 7. Start the backend

```powershell
cd backend
uvicorn app.main:app --reload
```

Use `--host 0.0.0.0 --port 8000` if you need an explicit bind.

## 8. Open API docs

- Health: http://localhost:8000/health
- Status: http://localhost:8000/status
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Legacy redirect: http://localhost:8000/api/docs → `/docs`
- UI shell: http://localhost:5173 (`npm run dev` in `frontend/`)

## 9. Run tests

From the repository root, with `.venv` active:

```powershell
pytest
```

From `backend/`:

```powershell
cd backend
pytest
```

Frontend:

```powershell
cd frontend
npm test
```

Lab CV is **optional** and **isolated**. Do not install OpenCV/Torch into the backend `.venv`. Use `.venv-cv` and [`cv/README.md`](../cv/README.md):

```powershell
.\.venv-cv\Scripts\python.exe -m pytest -c pytest-cv.ini -v -rs
```

Set `ILKA_CV_PERSON_WEIGHTS` to a local `.pth` whose SHA-256 matches the pin in `cv/detectors/person_cpu.py` (see `.env.example`). `CpuPersonDetector` does not download weights. Without that verified file, or without optional CPU packages in `.venv-cv`, local pytest skips the live smoke. Root `pytest` collects `tests/cv_ai/` through `pytest.ini` and skips the same way. The GitHub `cv-cpu-smoke` job fetches the artifact with the checksum script, sets the variable, and fails if the smoke test is skipped.

Apply migrations against Postgres (not SQLite unit tests). From the repo root, with `.env` loaded:

```powershell
python scripts/dev/alembic_safe.py current
python scripts/dev/alembic_safe.py upgrade head
```

Or from `backend/` after `DATABASE_URL` or `ILKA_POSTGRES_URL` is set:

```powershell
alembic upgrade head
alembic revision --autogenerate -m "message"
```

Health/readiness:

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/status
curl http://localhost:8000/ready
```

`/health` is 200 without a database. `/status` is 200 and never includes credentials. `/ready` is 200 when Postgres (or the configured SQLAlchemy URL) is reachable.

Protected identity APIs (`/api/me`, `/api/sites`, camera registry) require a valid ILKA session bearer token. Full credential authentication is **SCAFFOLDED**; `POST /api/v1/auth/login` returns 501 until implemented. Production requires `AUTH_SECRET_KEY` for signing session tokens. Keep the secret in vault or `.env` only. Pytest uses in-process HMAC test tokens; it does not call an external identity provider. See [authentication.md](./authentication.md).

## Environment variables

- `APP_NAME` / `APP_ENV` / `DEBUG`: application label, environment alias, local debug flag (`APP_ENV` maps to `ENVIRONMENT`)
- `ENVIRONMENT`: development | testing | production
- `DATABASE_URL`: canonical runtime variable. Optional for `/health` and `/status`; required for `/ready` (or fallback below) and **required by name** for production startup
- `ILKA_POSTGRES_URL`: Neon (or CI/Compose) Postgres URL in `.env` only. If `DATABASE_URL` is empty, development and tests use `ILKA_POSTGRES_URL`. Production must set `DATABASE_URL`
- `AUTH_SECRET_KEY`, `AUTH_ALGORITHM`, `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES`, `AUTH_REFRESH_TOKEN_EXPIRE_DAYS`: see [authentication.md](./authentication.md). Production requires `AUTH_SECRET_KEY`
- `ILKA_CV_PERSON_WEIGHTS`: optional local detector weights. The process does not download this file. The digest must match the pin before load
- GitHub Actions integration tests inject a disposable Postgres URL. They do not use Neon.

Neon development (same line in `.env`, then save):

```text
ILKA_POSTGRES_URL=<your-neon-connection-string>
```

## Postgres integration tests

Must not skip when `ILKA_POSTGRES_URL` is set:

```powershell
python scripts/dev/verify_postgres_env.py
pytest tests/integration
```

Without `ILKA_POSTGRES_URL`, integration tests skip. Do not put Neon URLs in git.

## Shutdown

Stop uvicorn and Vite (Ctrl+C). `docker compose down` if you started Postgres.

## Troubleshooting

- `/ready` is 503: no `DATABASE_URL` / `ILKA_POSTGRES_URL` or database unreachable. `/health` and `/status` can still be 200.
- Protected routes return 401: missing/invalid bearer token, or authentication is not configured. There is no development header bypass.
- CORS errors: add the UI origin to `API_CORS_ORIGINS`.
- Docker not installed: use Neon or skip `/ready` until a database exists.
- Never put RTSP passwords or Neon URLs in git.

Redis is **not** started (ADR 0006).
