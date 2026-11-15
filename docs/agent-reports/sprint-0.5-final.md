# Sprint 0.5 final

**Date:** 2026-08-20  
**Status:** Foundation **hardened in-repo**. **NOT READY for Sprint 1** (cameras/RTSP/CV).

## Done

| Item | Result |
| :--- | :--- |
| Auth ADR | **0010** hybrid OIDC + ILKA authorization. Login **not** implemented |
| RBAC structure | `Principal`, org/site/permission helpers; `GET /api/v1/me` → **401** |
| Postgres tests | Written; **skipped locally**; CI job added with Postgres 16 |
| Alembic | `0002_auth_prep` (`idp_subject`, tenant indexes) |
| Health/ready | Health 200 without DB; ready 503 if unset; boom only in testing |
| Logging | `request_id` via contextvars; allow-listed context |
| Frontend | `src/services/api.ts` + 3 health client tests; build OK |
| Secrets | Classification doc; no `.env` committed |
| Docker | Static review only (CLI missing) |

## Tests (this workstation)

- pytest unit: **20 passed**
- pytest integration: **3 skipped** (no `ILKA_POSTGRES_URL`)
- ruff: pass
- vitest: **4 passed**; `npm run build`: pass
- GitHub Actions: **not run**
- Docker Compose: **not run**

## Independent reviews

Cursor QA/Security only. **Codex and Claude were not executed.** Files `codex-review.md` / `claude-review.md` say so.

## Git

Branch `feature/sprint-0-foundation`, **no commits**. `git config user.name` / `user.email` were **empty** — agent did not invent identity and did not commit.

## Residual HIGH

Neon/hosted `/ready` and remote CI remain human ops. npm audit MEDIUM remains.

## Stop

Do **not** start Sprint 1 until a human: sets git identity and commits, connects GitHub, provisions Neon **dev** or runs Compose Postgres, and accepts remaining MEDIUM dependency risk.
