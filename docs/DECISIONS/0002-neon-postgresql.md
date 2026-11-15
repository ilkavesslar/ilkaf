# ADR 0002: Neon PostgreSQL as system of record

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

The program already standardized on hosted Postgres (Neon). A local server was not required by the scaffold.

## Decision

Neon PostgreSQL is the transactional source of truth. No local Postgres unless a later ADR requires air-gap/dev parity. Agents must not use production credentials.

## Consequences

Dev/test via Neon branches. Migration tool still **NOT DECIDED**.
