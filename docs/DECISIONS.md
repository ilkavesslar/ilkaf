# Architecture decisions

Record only what is actually decided. ADRs: [`DECISIONS/`](./DECISIONS/).

Status: **APPROVED** | **PROVISIONAL** | **NOT DECIDED**

## APPROVED

| ID | Decision | ADR |
| :--- | :--- | :--- |
| A1 | Neon PostgreSQL is the system of record | 0002 |
| A2 | Frontend direction: React + TypeScript | |
| A3 | Backend direction: Python 3.11+ | |
| A4 | OpenAPI 3 when an API exists | |
| A5 | HITL (or explicit audited policy) for safety-critical / punitive actions | 0007 |
| A6 | Cursor is the primary implementation environment | |
| A7 | GitHub for source control (remote not connected yet) | |
| A8 | Modular monolith; extract services only with a new ADR | 0001 |
| A9 | Multi-agent governance (`AGENTS.md`, `CODEX.md`) | |
| A10 | Observation ≠ incident; staged pipeline | 0003 |
| A11 | PoE IP cameras + vendor adapters; webcams are mock-only | 0004 |
| A12 | Edge/hybrid inference allowed; not cloud-only | 0005 |
| A13 | No Redis/event bus in Phase 1; Postgres SoR even later | 0006 |
| A14 | Software does not guarantee physical safety | 0007 |
| A16 | FastAPI + SQLAlchemy 2 + Alembic + Vite | 0008 |
| A17 | Optional Compose Postgres for local/CI | 0009 |
| A18 | Hybrid OIDC authentication + ILKA authorization records | 0010 |

## PROVISIONAL

| ID | Item |
| :--- | :--- |
| P1 | FastAPI + SQLAlchemy 2 async | Accepted in ADR 0008 |
| P2 | Vite | Accepted in ADR 0008 |
| P3 | Docker / Compose | Optional Postgres only (ADR 0009) |
| P4 | Redis Streams (deferred — ADR 0006) | |
| P5–P6 | Specific AI/CV frameworks | |
| P7 | RTSP/ONVIF as default ingest/management (likely, not locked to a vendor) | |
| P8 | Browser video protocol | |
| P9 | Edge runtime (TensorRT / ONNX / PyTorch) | |
| P10 | Migration tool | Alembic accepted in ADR 0008 |

## NOT DECIDED

N1–N2 frontend/backend internals; N3 auth **protocol** decided (OIDC, ADR 0010) — IdP **product** still open; N4 RBAC **scopes** documented, login not implemented; N5 camera SKUs; N6 model families; N7–N8 deploy/cloud; N9 PLC; N10 PII redaction location; plus cameras-per-node and retention (requirements open questions).

## Out of scope until an ADR

Kubernetes, Redis MCP, cloud-provider MCP, local Postgres, Sentry SDK, extra microservices.
