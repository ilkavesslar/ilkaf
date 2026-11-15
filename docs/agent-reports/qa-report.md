# Sprint 0.5 QA/Security report

**Agent:** QA + Security (Cursor, same workspace — not an independent Codex/Claude run)  
**Tests run:** `pytest tests/unit` (**20 passed**), `pytest tests/integration` (**3 skipped**, no `ILKA_POSTGRES_URL`), `ruff check app` (pass), `npm test` (**4 passed**), `npm run build` (pass). Docker CLI **missing**. GitHub Actions **not** executed (no remote). Git **author identity unset** — no commit from this agent.

## Findings

### [HIGH] Hosted Postgres / Neon still unverified

- **Where:** ops, `.env` (absent), no Neon project in-repo
- **Why:** CI Postgres job is written but has not run on GitHub. Local integration tests skipped.
- **Fix:** Human: Docker Desktop or Neon **dev** URL in `.env`; enable Actions after a remote exists
- **Status:** Open (environmental). Does not block merging foundation *code*, does block claiming Postgres is proven on this machine.

### [MEDIUM] Frontend npm audit chain (Vite/esbuild/vitest, react-router)

- Unchanged from Sprint 0. Do **not** `npm audit fix --force`.
- **Status:** Open; accepted as MEDIUM for production API (dev-server class).

### [MEDIUM] SQLite unit tests vs Postgres production dialect

- Mitigated by CI `backend-postgres` job; **not proven locally**.
- **Status:** Partially addressed.

### [LOW] `/__test/boom` in `ENVIRONMENT=testing` only

- Development returns 404 (tested).
- **Status:** Acceptable.

### [INFO] Login not implemented

- `/api/v1/me` is **401**. No fake users. Correct for ADR 0010.

## Secrets

`.env` not present. Compose password classified as local placeholder (`docs/agent-reports/secret-classification.md`).

## Verdict

**REVISIONS REQUIRED** for full DoD (Neon, remote CI, git identity, Docker run). **No CRITICAL** in code reviewed this sprint. **Not READY for Sprint 1 cameras.**
