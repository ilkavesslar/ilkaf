# Event architecture

**Status:** **PLANNED**. No broker **IMPLEMENTED**. Redis Streams are **PROVISIONAL** and **not** selected for Phase 1.

## Phase 1 (approved shape)

**PostgreSQL (Neon) is the system of record** for users, sites, later observations/events/incidents, and audit. The first API can create rows in the same request as the command (no Redis).

Why this is appropriate now:

- One moving part; matches A1/A8.
- Transactions, uniqueness, and audit in one place.
- No Redis operations burden while there is no ingest load.

Limits: not a high-throughput camera bus; long-polling/WebSocket fan-out comes later; replay is SQL queries, not a log.

## When ingest exists

In-process queue inside the monolith is enough for a **small** camera count. If backpressure or multiple processes appear, **then** evaluate:

| Option | Fit | Cost |
| :--- | :--- | :--- |
| Postgres (`LISTEN/NOTIFY` or skip-locked jobs) | Low volume, strong consistency | Limited fan-out |
| Redis Streams | Lightweight stream, consumer groups | New ops; **P4** |
| Later Kafka/NATS | High volume, multi-site | Premature now |

## Requirements for any future bus

- **Ordering:** per camera (or per track) is enough; global order is not required.
- **Idempotency:** event ids; consumers must be safe to retry.
- **Replay:** retain observations in Postgres even if a bus is added.
- **Poison/DLQ:** failed rule evaluation must be visible, not dropped.
- **Failure:** bus down → **event processing unavailable** (observable); do not pretend detections still reach operators.

## Migration path

Postgres SoR remains. A broker, if added, is a **delivery** mechanism. Do not make Redis the source of truth for incidents.
