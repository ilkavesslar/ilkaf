# Sprint 0 architecture review

**Agent:** Architect  
**Date:** 2026-08-20  
**Decision:** Proceed with foundation implementation (this sprint is the approval to accept FastAPI/Vite/Alembic for the modular monolith).

## Existing stack (as-is)

| Area | Status |
| :--- | :--- |
| Backend/frontend/db | **SCAFFOLDED** empty dirs (`backend/app/*`) |
| Neon Postgres | **APPROVED** SoR; no project wired |
| FastAPI, Vite, Alembic, Docker | **PROVISIONAL** — accept for Sprint 0 via ADR 0008/0009 |
| Redis, CV, cameras | Out of scope |
| Auth mechanism (JWT vs IdP) | **NOT DECIDED** — no login API this sprint |
| CI, Dockerfiles | Missing |

Preserve: folder layout, `.gitignore`, `.env.example` pattern, docs, Cursor rules.

## Sprint 0 plan

| Topic | Choice |
| :--- | :--- |
| Backend | FastAPI in `backend/app/` |
| Frontend | React + TS + Vite in `frontend/` |
| Database | SQLAlchemy 2 async; Alembic; Postgres (Neon or Compose) |
| Auth | Role **enum** + org/user/site **tables only**; no JWT login |
| API | `/health`, `/ready` unversioned; JSON API under `/api/v1` |
| Tests | pytest + httpx; SQLite in-memory for unit tests; skip live PG if unset |
| Docker | Optional Compose Postgres + API/UI — not required to run unit tests |
| Logging | JSON stdout; request id; no secrets |
| Config | pydantic-settings; `.env` gitignored |
| CI | GitHub Actions: ruff, pytest, `npm run build` |
| Security | CORS allowlist; no credentials in git; RBAC documented not enforced on routes yet |
| Observability | health/ready + structured logs only |

## Conflicts

- Roadmap said Sprint 0 is ops-only; this sprint **is** the first code. Treat as combined 0+thin-1 foundation, **without** login or cameras.
- Local Compose Postgres vs “no local Postgres”: **optional** for Docker users/CI; Neon remains SoR (ADR 0009).

## Not this sprint

PPE, RTSP, incidents, Redis, microservices, Sentry SDK, real auth.
