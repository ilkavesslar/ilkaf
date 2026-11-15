# API specification

**Status:** **PLANNED**. No OpenAPI file, no server (**SCAFFOLDED** `backend/` only). FastAPI is **PROVISIONAL**. WebSockets are **PLANNED**, not Phase 1 required.

## Planned resource areas (not implemented)

- Auth: login, refresh, logout
- Users, roles, employees
- Sites, buildings, floors, zones
- Cameras, health, (future) signed view URLs
- Incidents, alerts, acknowledgements
- Audit logs, reports
- Notifications

## Contracts

When an API exists, publish OpenAPI 3 and keep frontend `types/` in sync. Until then, do not invent endpoint paths as if they were stable.

Error envelopes, pagination, and WebSocket topic ACLs are **TODO**.

Related: `docs/api/README.md`.
