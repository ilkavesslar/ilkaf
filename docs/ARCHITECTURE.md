# ILKA architecture

**Status:** Sprint 2 identity is **IMPLEMENTED** (token validation, RBAC, site scope, camera **metadata** registry). Auth0/OIDC has been removed; custom ILKA authentication is **SCAFFOLDED**. Sprint 3 **lab CV** in `cv/` is present for lab validation (PROVISIONAL): `FileSource`, `Observation`, CPU person detector, lab CLI. Independent QA/security review and human closure remain pending. Production readiness and accuracy certification remain open. RTSP/ONVIF ingest, a production CV HTTP API, the operations dashboard, and the Detection → Event → Incident pipeline remain open.

Target system: [SYSTEM-ARCHITECTURE.md](./SYSTEM-ARCHITECTURE.md). How to run: [DEVELOPMENT.md](./DEVELOPMENT.md).

Narrative diagrams: `docs/architecture/README.md` (treat that matrix as mixed APPROVED/PROVISIONAL — source of truth is `docs/DECISIONS.md`).

## Target pipeline (later sprints)

Sprint 2 adds authentication, authorization, and site-scoped APIs on the Sprint 1 foundation. Sprint 3 adds **lab** file-source CV only. Live factory cameras, RTSP, a CV HTTP API, and the dashboard remain **PLANNED**.

```text
                   ILKA
                    |
              Authentication
                    |
              Custom Auth
                    |
              User Identity
                    |
          ┌─────────┴─────────┐
          |                   |
        Roles             Permissions
          |                   |
          └─────────┬─────────┘
                    |
               Site Scope
                    |
          ┌─────────┴─────────┐
          |                   |
        Sites              Cameras
                              |
                         Metadata Only
```

Future (not Sprint 2):

```text
Camera Streams → Computer Vision → Safety Rules → Safety Events → Alerts
```

| Layer | Responsibility now | Later |
| :--- | :--- | :--- |
| FastAPI backend | Health/status, custom auth/RBAC, site APIs, camera metadata | Events, live video, dashboard |
| Database (PostgreSQL) | Connection, sessions, Alembic, identity schema | Detections, zones, alerts |
| AI / CV (`ai/`, `cv/`) | Lab `cv/` FileSource, Observation, provisional CPU person detector, lab CLI | RTSP ingest, tracking, PPE, events, production models |
| Cameras (`cameras/`, metadata APIs) | Camera **metadata** registry; `cameras/` dir **SCAFFOLDED** | RTSP, stream health, live registration adapters |
| Web dashboard (`frontend/`) | Placeholder shell | Operations UI |

ILKA stays a **modular monolith** for Phase 1: one API process, one PostgreSQL database. Do not split microservices until an ADR records a need.

## What exists

| Directory | Intended role | Status |
| :--- | :--- | :--- |
| `frontend/` | React + TypeScript + Vite shell | **IMPLEMENTED** (placeholders only) |
| `backend/` | FastAPI + OIDC/RBAC + sites + camera metadata | **IMPLEMENTED** (no CV/RTSP) |
| `cameras/` | Camera infrastructure placeholder | **SCAFFOLDED** |
| `cv/` | Lab FileSource, Observation, provisional CPU person detector, lab CLI (module, not a service) | **IMPLEMENTED** — **LAB / PROVISIONAL** (no RTSP, no CV HTTP API) |
| `ai/` | Temporal scoring (module, not a service) | **SCAFFOLDED** |
| `database/` | Historical placeholder dir; Alembic lives in `backend/alembic/` | **SCAFFOLDED** |
| `compose.yaml` | Optional Postgres + API | **IMPLEMENTED** (optional) |
| `tests/` | pytest + Vitest | **IMPLEMENTED** (foundation) |

## Phase 1 (smallest useful system)

Do **not** start this until GitHub + Neon **development** project exist and quality gates are followed.

```text
[ React + TypeScript UI ]
          │
          ▼
[ Single Python backend process ]
          │
          ▼
[ Neon PostgreSQL — development project / branch ]
```

- One frontend, one backend, one database.
- `cv/` and `ai/` remain **packages/modules** inside the repo, not separate production services.
- No Redis, workers, notification service, camera microservice, or Kubernetes in Phase 1.
- First vertical: organization, identity, one site, audit — not live video.
- Canonical long-term model (including observation/event): [DATABASE-ARCHITECTURE.md](./DATABASE-ARCHITECTURE.md).

Later CV/AI/cameras attach to the same backend until isolation is proven.

## Later (planned, not Phase 1)

Industrial RTSP → `cv/` → `ai/` → backend → dashboard. Browser protocol **PROVISIONAL**.
