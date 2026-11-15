# Database architecture

**Status:** Foundation identity tables **IMPLEMENTED** (Alembic). Full domain remains **PLANNED**. Phase 1 field-level notes: [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md).

**SoR:** Neon PostgreSQL (**APPROVED**). Optional Compose Postgres for local/CI (ADR 0009).

## Tenant isolation

`organization` is the tenancy root (**PLANNED**; missing from the earlier Phase 1 sketch). All site-scoped tables include `organization_id`. Application queries must filter it; do not rely on “we only have one plant” forever.

## Canonical domains (logical)

```text
organization ─┬─ user / role
              ├─ user_site_assignments (user ↔ site, same organization_id)
              ├─ site ─┬─ building → floor → zone
              │        ├─ employee
              │        ├─ camera / device
              │        ├─ safety_rule
              │        └─ camera_zone_overlay
              ├─ model_version
              ├─ observation → detection → safety_event
              ├─ incident ← verification
              ├─ alert → acknowledgement / escalation
              └─ audit_log
```

| Entity | Module | Phase 1? |
| :--- | :--- | :--- |
| organization | backend | **yes** (single row allowed) |
| user, role | backend | **yes** (coarse roles) |
| user_site_assignments | backend | **yes** (membership; not a permission matrix) |
| site | backend | **yes** |
| audit_log | backend | **yes** |
| building, floor, zone | backend / twin | no |
| employee | backend | no (PII) |
| camera, device | backend + cv config | no (metadata sprint later) |
| safety_rule | backend | no |
| observation, safety_event | cv/ai → backend | no |
| incident, alert, ack, escalation | backend | no |
| model_version | ai | no |

## Conflicts with earlier docs

- `docs/architecture/README.md` still diagrams **Redis** as if selected — it is **PROVISIONAL** only; ignore for Phase 1.
- First domain model omitted **organization** and **observation/event** stages. This file is authoritative for the long-term model; `DATABASE_SCHEMA.md` stays the Phase 1 field list.

## Migrations

Tool **Alembic** (ADR 0008). Versioned, reversible, never ad-hoc production DDL.
