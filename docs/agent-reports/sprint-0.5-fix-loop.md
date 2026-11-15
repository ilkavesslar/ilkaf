# Sprint 0.5 review fix loop — implementation

**Agent:** Builder
**Date:** 2026-08-21
**Branch:** `feature/sprint-0-foundation` (no commit, no push)

## Objective

Resolve valid mandatory independent-review findings F-001, F-002, F-003, F-004, F-005, F-010 without starting Sprint 1, cameras, RTSP, CV, or AI.

## Decisions

- **F-001:** Document required `main` ← `develop` topology. Do not push or create remote protected branches.
- **F-002:** Fail-closed mutating `/api/` gate (401). No OIDC client, no passwords, no app-minted JWTs, no trusted headers.
- **F-003:** Root `SECURITY.md` follows ADR 0010; password/JWT minting marked obsolete for Phase 1.
- **F-004:** `user_site_assignments` with composite FKs for organization isolation. No camera tables.
- **F-005:** Keep Neon/asyncpg URL resolution; production still requires `DATABASE_URL` by name.
- **F-010:** Remove `python-dotenv` usage. Settings / explicit env / `.env` parse without that import.

## Unresolved

- Remote `main` / `develop` still missing until a human creates and protects them.
- OIDC login still not implemented (intentional).
