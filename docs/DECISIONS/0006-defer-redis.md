# ADR 0006: Defer Redis (and any event bus)

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

Older diagrams assumed Redis Streams. Nothing in the repo uses Redis. Phase 1 has no ingest load.

## Decision

Phase 1 uses PostgreSQL only for persistence and in-process flow. Redis remains **PROVISIONAL**. Revisit when camera ingest needs consumer groups or multi-process backpressure. Postgres stays SoR even if a bus is added.

## Consequences

Fewer dependencies now. Must not pretend Redis is production-ready.
