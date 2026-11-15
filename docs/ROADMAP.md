# Roadmap

**Status:** Sprints 0–2 foundation code and Sprint 3 **lab CV (M1–M5)** implementation are present in this repository. Sprint 3 is lab validation only. Independent QA/security review and human closure remain pending. Production readiness, accuracy certification, and production camera ingest remain open. No Sprint 4 is defined here.

## Phases

| Phase | Goal | Includes | Excludes |
| :--- | :--- | :--- | :--- |
| 0 | Foundation | Docs, Cursor, secrets hygiene, GitHub connect, Neon **dev** | App features |
| 1 | Modular monolith slice | Org, user, role, site, audit, OpenAPI stub, tests | CV, Redis, Docker requirement, live video |
| 2 | Camera registry | Metadata, secrets refs, health **stub** | RTSP decode, models |
| 3 | Ingest module | One adapter, reconnect, camera-unavailable | Full multi-model suite |
| 4 | Observations → events | Thresholds, persistence, de-dupe, rules | Auto-incident without policy |
| 5 | HITL incidents/alerts | Ack, audit, dashboard | Physical sirens unless ADR |
| 6 | Edge/hybrid | Optional on-prem inference | Kubernetes by default |
| 7 | Hardening | Load, security test, staging | Treating software as a safety SIL |

**Phase 3** (eventual production ingest: RTSP/ONVIF adapter, reconnect, camera-unavailable) is **separate** from **named Sprint 3**, which is lab FileSource CV only. Phase 3 work is **not** started by closing Sprint 3.

## Sequencing

Sprints 0–2 and Sprint 3 lab CV are already in this repository. The steps below are that history. They are not a request to implement Sprint 1 again.

1. Foundation docs, Git workflow, and secrets hygiene.
2. FastAPI, Vite, and Alembic, recorded in ADR 0008.
3. Sprint 1 code: API shell, UI shell, and the organization, user, role, site, and audit substrate.
4. Sprint 2 camera **metadata** registry (no stream), after that substrate.

This file does not record branch protection for `main`, a Neon development project, or Docker Desktop as finished. Those remain **human ops**.

## Named sprints in the repository

**Sprint 0.5:** Auth ADR, RBAC helpers, and Postgres CI integration. Camera streams were outside that sprint.

**Sprint 1:** Python API (FastAPI, ADR 0008), migrations, identity substrate, one site, audit, React shell, pytest, and CI lint/test. This code is present. It is not a production deploy.

**Sprint 2:** Identity/OIDC, RBAC, site scope, and camera **metadata** registry (no stream). OpenAPI for those APIs. Playwright login smoke remains **not** the product E2E suite.

**Sprint 3 (lab CV, M1–M5):** Local-file computer vision for lab validation. Independent QA/security review and human closure remain pending. This is not production camera ingest, production readiness, or accuracy certification.

| Milestone | Scope |
| :--- | :--- |
| M1 | `FileSource`, `VideoSource`, `Frame`, bounded buffer, `[MOCK / SYNTHETIC]` labels |
| M2 | `BoundingBox` / `Observation` contract (not incidents) |
| M3 | **PROVISIONAL** CPU person detector (SSDLite320 MobileNetV3-Large); not a production model ADR |
| M4 | Lab preview CLI (`scripts/dev/preview_person_detection.py`) |
| M5 | Quality tests, isolated smoke, lab-evidence notes |

Sprint 3 **non-goals** (still **PLANNED** / later phases): RTSP/ONVIF; reconnect and camera-unavailable production ingest; PPE detection; tracking; events, incidents, and alerts; operations dashboard; production model ADR / model selection.

Do not start an undefined later sprint from this file. The next intended work is **Phase 3** production ingest and the later rows in the phase table. Named Sprint 3 does not start or close that work.
