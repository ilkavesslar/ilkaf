# Codex-style notes (Sprint 0.5)

**This is not an independent Codex review.** Cursor documented expected Codex checks. A human should run Codex (or equivalent) on the diff.

## Expected verdict if Codex agrees with local evidence

- **Critical:** 0 (from Cursor QA)
- **High:** hosted Postgres/CI still unverified on this workstation
- **Medium:** npm audit chain; SQLite vs Postgres until Actions runs
- **Ask Codex to confirm:** Alembic `0002` unique on nullable `idp_subject`; 401-only authz; no secret leakage in logs

Do not treat this file as a rubber-stamped independent review.
