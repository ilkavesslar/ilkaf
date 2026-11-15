# System architecture

**Status:** **PLANNED** target. Repo modules **SCAFFOLDED**. Nothing **IMPLEMENTED**.

Current clone vs this target: [ARCHITECTURE.md](./ARCHITECTURE.md). Decisions: [DECISIONS.md](./DECISIONS.md).

## Current architecture (as-is)

Empty module directories plus governance docs. No processes, no schema, no API, no UI. Intended folders already match a modular monolith (`frontend/`, `backend/`, `cv/`, `ai/`, `database/`, `tests/`).

## Target architecture (to-be)

```text
 PoE IP cameras (vendor-agnostic adapters)
        │ RTSP / ONVIF management where supported
        ▼
 Edge node (optional)          Central industrial server / later hybrid cloud
  cv ingest + inference    or   same modules in one backend process
        │ observations (not incidents)
        ▼
 backend/  — rules, verification, incidents, alerts, RBAC, audit
        │
        ▼
 Neon PostgreSQL (system of record)
        │
        ▼
 frontend/  — operator dashboard (HITL)
```

**Phase 1** omits cameras/CV: UI + API + Postgres only.

## Module boundaries (not microservices)

| Module | Owns | Does not own |
| :--- | :--- | :--- |
| `frontend/` | Operator UX, session UI | Business rules, secrets, inference |
| `backend/` | AuthZ, tenants/sites, rules, incident lifecycle, APIs | Frame decode, model weights |
| `cv/` | Stream adapters, frames, detectors, tracks | Incident confirmation, alerting policy |
| `ai/` | Temporal scoring, persistence windows, duplicate suppression assist | HITL decisions |
| `database/` | Migrations, seeds | Runtime connections (app config) |

Extract a **service** only when scale, isolation, team, or reliability evidence exists (ADR required).

## Multi-site / tenants

**PLANNED:** `Organization` (tenant) → `Site` → spatial tree → cameras. Every operational row carries `organization_id` (and usually `site_id`). Phase 1 may start with a single organization row so the column exists early.

## Hybrid / edge

Inference may run next to cameras, on a site workstation, on a central server, or split (edge observations, central rules). The backend consumes **observation/event contracts**, not vendor SDKs. Cloud-only inference is **not** a Phase 1 assumption. Offline: buffer observations locally; sync when the link returns; never invent “safe” during an outage.

## Software vs physical safety

ILKA does not replace site safety procedures, interlocks, or human supervision. Availability of monitoring is itself a safety-relevant signal.

## Related

Cameras: [CAMERA-ARCHITECTURE.md](./CAMERA-ARCHITECTURE.md). Pipeline: [AI-PIPELINE.md](./AI-PIPELINE.md). Events: [EVENT-ARCHITECTURE.md](./EVENT-ARCHITECTURE.md).
