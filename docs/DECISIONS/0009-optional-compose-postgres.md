# ADR 0009: Optional Compose PostgreSQL for local and CI

- **Status:** Accepted (Sprint 0)
- **Date:** 2026-08-20

## Context

A1: Neon is the hosted SoR. Sprint 0 also needs a way to run Postgres without requiring every laptop to use Neon.

## Decision

- **Neon** remains the intended shared development/production Postgres.
- **Docker Compose PostgreSQL** is **optional** for local/CI only. It is not a second production database.
- Unit tests may use **SQLite in-memory** so pytest runs without Docker or Neon.
- Redis is still **not** introduced (ADR 0006).

## Consequences

Document two DATABASE_URL sources. Never commit real Neon URLs.
