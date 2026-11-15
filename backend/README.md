# Backend (Python 3.11+)

Sprint 2–3: FastAPI, `/health`, `/status`, `/ready`, custom-auth skeleton `/api/v1/auth/*`, protected `/api/me` and site/camera-metadata APIs, SQLAlchemy, Alembic, logging. No RTSP or incident APIs.

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e "./backend[dev]"
```

Or from `backend/`:

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

OpenAPI: http://localhost:8000/docs  
See `docs/DEVELOPMENT.md`.
