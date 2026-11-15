# ILKA

**Intelligent Industrial Safety Monitoring Platform**

This repository is currently **private / on-premise**. It is not a public SaaS product.

> [!NOTE]
> **Status vocabulary:** **IMPLEMENTED** (running code) · **SCAFFOLDED** (folders/docs only) · **PLANNED** · **PROVISIONAL** (tech not locked).
>
> **Sprint 2–3 status:** identity **IMPLEMENTED** (token validation, RBAC, site-scoped APIs, camera metadata registry). Auth0/OIDC removed; custom ILKA authentication is **SCAFFOLDED**. Sprint 3 **lab CV** in `cv/` is present for lab validation (FileSource, Observation, provisional CPU person detector, lab CLI). Independent QA/security review and human closure remain pending. Production readiness, accuracy certification, RTSP ingest, PPE/incident pipelines, camera streaming, and the operations dashboard remain open. License: [LICENSE](./LICENSE).

**Local setup (start here):** [docs/development/startup.md](./docs/development/startup.md) · detail: [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md) · Intel Mac CV: [docs/development/mac-setup.md](./docs/development/mac-setup.md) · docs index: [docs/README.md](./docs/README.md)

---

## Purpose and factory use case

ILKA is an industrial safety monitoring platform for a factory that manufactures protective overalls. The long-term system will use on-premise cameras and computer vision to watch for PPE gaps, restricted-zone entry, and person–vehicle proximity hazards, then surface events on a web dashboard with historical analytics.

Privacy and reliability matter: the intended deployment is primarily on-premise.

## Planned capabilities

1. PPE violations (helmet, safety vest, gloves)
2. Restricted-zone violations
3. Person–vehicle proximity hazards
4. Real-time factory camera monitoring
5. Safety events and alerts
6. Historical safety analytics
7. A web dashboard

Sprint 1 did not include computer vision. Sprint 3 lab CV is file-source only (not RTSP, YOLO-as-product, or the dashboard). Production camera/CV product work remains **planned**.

## Architecture

Sprint 1 is a **modular monolith**: one FastAPI process and PostgreSQL. Target pipeline (later sprints):

```text
Factory Cameras → Camera Layer → Computer Vision / AI → Detection
    → Safety Rule Engine → Safety Event System → Database
    → FastAPI Backend → Web Dashboard
```

Details: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) (same file as `docs/architecture.md` on Windows). Safety concepts: [docs/safety-rules.md](./docs/safety-rules.md).

## Technology stack (Sprint 1)

- **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic Settings
- **Database:** PostgreSQL, SQLAlchemy 2 (async + asyncpg), Alembic
- **Tests:** Pytest, HTTPX / Starlette TestClient
- **Frontend shell:** React + TypeScript + Vite (placeholder only)
- **Backend venv:** PyTorch, CUDA, YOLO, and OpenCV are **not** backend dependencies. Optional lab CV uses isolated `.venv-cv` (see `cv/README.md`).

## Repository structure

```text
backend/     FastAPI application, Alembic, requirements
frontend/    Dashboard placeholder (later sprint)
ai/          CV/AI placeholder (later sprint)
cameras/     Camera infrastructure placeholder (later sprint)
cv/          Lab CV module (FileSource, Observation, provisional CPU person detector; not RTSP)
docs/        Architecture and development documentation
scripts/     Developer helpers
tests/       Pytest suites (unit / integration)
```

## Local setup (summary)

Requires **Python 3.11+** and **Node 20+** (Node 22 preferred). Keep environments separate: `.venv` (API), `frontend/` (UI), `.venv-cv` (lab CV on Intel Mac).

```bash
cp .env.example .env          # then edit locally; never commit .env
python3.11 -m venv .venv
source .venv/bin/activate
pip install --prefer-binary -e "./backend[dev]"
cd frontend && npm install && cd ..
# Optional lab CV (Intel Mac):
python3.11 -m venv .venv-cv
.venv-cv/bin/pip install --prefer-binary -r cv/requirements-detector-macos-x86_64.txt
.venv-cv/bin/python scripts/dev/fetch_person_detector_weights.py
.venv/bin/python scripts/dev/check_development_environment.py
```

Full daily workflow (backend / frontend / CV terminals): [docs/development/startup.md](./docs/development/startup.md).

## Start the backend

```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- http://localhost:8000/health
- http://localhost:8000/status
- http://localhost:8000/docs
- http://localhost:8000/redoc
- Frontend: `cd frontend && npm run dev` → http://localhost:5173/

## Run tests

```bash
.venv/bin/python -m pytest
.venv-cv/bin/python -m pytest -c pytest-cv.ini -v -rs   # lab CV, optional
cd frontend && npm test
```

## Environment configuration

Configuration is environment-variable driven (`backend/app/core/config.py`). Templates: `.env.example` and `backend/.env.example`. Do not hard-code credentials.

## Current Sprint 2 status

**IMPLEMENTED:** Sprint 1 foundation plus OIDC bearer validation, provisioned user identity, roles/permissions, site assignments, `/api/me`, site APIs, camera **metadata** registry, auth tests.

**NOT IMPLEMENTED:** production detection, RTSP/streaming, alerts, IdP login UI, operations dashboard, production deploy. Lab `cv/` file-source observations stay `[MOCK / SYNTHETIC]`.

---

## 1. What is ILKA?

**ILKA** is an enterprise-grade, mission-critical industrial safety platform designed for modern manufacturing plants, warehouses, construction environments, and hazardous industrial facilities.

ILKA bridges the gap between high-throughput computer vision, spatial edge computing, automated safety event processing, and human-in-the-loop operational oversight.

---

## 2. The Problem It Solves

Industrial workplaces face persistent safety hazards, regulatory non-compliance, and severe occupational injury risks:

- **Delayed Hazard Identification**: Traditional CCTV systems rely on passive recording or fatigued human monitors, resulting in delayed responses to critical safety breaches.
- **PPE Non-Compliance**: Inconsistent adherence to Personal Protective Equipment (PPE) requirements (hard hats, high-visibility vests, protective eyewear, gloves).
- **Restricted Zone Incursions**: Unauthorized pedestrian intrusion into heavy machinery, robotic cell, or forklift operating perimeters.
- **Unverified AI Decisions**: Naive AI tools that trigger false alarms or lack explainability, eroding operator trust.
- **Fragmented Incident Audit Trails**: Inability to reconstruct precise timelines, camera views, and operator actions during regulatory audits or post-incident investigations.

---

## 3. Major Planned Capabilities

- **Real-Time Video Stream Ingestion**: Resilient decoding and processing of multi-camera RTSP/ONVIF feeds at the edge.
- **Automated Hazard Detection (CV)**: Real-time detection of PPE violations, restricted zone intrusions, slip/trip events, and machinery proximity breaches.
- **Temporal Pattern & Anomaly Scoring (AI)**: Time-series analysis of near-misses, high-frequency hazard zones, and predictive safety heatmaps.
- **Human-in-the-Loop (HITL) Operations Dashboard**: Real-time operations console for plant operators to review, acknowledge, verify, and resolve safety incidents.
- **Role-Based Access Control (RBAC)**: Fine-grained permissions for Operators, Safety Officers, Plant Managers, and Compliance Auditors.
- **Immutable Audit Logging & Compliance Reporting**: OSHA/ISO-aligned incident reporting with synchronized video snapshots and operator timestamps.

---

## 4. High-Level Architecture

```text
  [ Industrial RTSP Cameras ]
             │
             ▼
   [ cv/ Stream Ingestion & Edge Inference ] ─── (Detections + Snapshots)
             │
             ▼
   [ ai/ Temporal & Anomaly Scoring ]
             │
             ▼
   [ backend/ Event Orchestrator & RBAC ] ─── [ database/ PostgreSQL ]
             │
             ├──► [ WebSocket Live Event Bus ]
             │
             ▼
   [ frontend/ Operations Dashboard (React + TS) ]
             │
             ▼
   [ Human Operator Verification / Action ]
```

---

## 5. Planned Technology Areas

- **Frontend**: React, TypeScript, Vite, Tailwind CSS / Vanilla CSS design system, HTML5 Canvas / WebRTC video renderers.
- **Backend**: Python 3.11+, FastAPI / Async IO, Pydantic, SQLAlchemy.
- **Computer Vision (CV)**: OpenCV, PyTorch / YOLO wrappers, DeepSORT / ByteTrack tracking algorithms, TensorRT edge acceleration. **Not in Sprint 1.**
- **Artificial Intelligence (AI)**: Scikit-learn, PyTorch, explainability toolkits, anomaly scoring models. **Not in Sprint 1.**
- **Database & State**: PostgreSQL with asyncpg, Alembic migrations. Redis is deferred (ADR 0006).
- **Infrastructure**: Docker, Kubernetes manifests, Helm, Terraform, Prometheus, Grafana (later / provisional).

---

## 6. AI & Computer Vision Philosophy

1. **Probabilistic Observations**: CV and AI outputs are treated as probabilistic sensor data with explicit confidence intervals, not infallible assertions.
2. **Explainability First**: Every detection includes bounding coordinates, timestamp, camera identifier, model version, and confidence score.
3. **Human-in-the-Loop**: Safety-critical alerts and punitive actions require explicit human operator confirmation.
4. **Fail-Safe Operation**: If a camera drops or an inference worker fails, the system immediately flags the blind spot to human safety managers.

---

## 7. Security Philosophy

- **Zero Trust Architecture**: Strict RBAC across all REST routes, WebSocket feeds, and data queries.
- **Worker Privacy by Design**: Automated PII masking (face/license-plate blurring) where applicable.
- **Encrypted Media & Transit**: TLS 1.3 for all data in motion; AES-256 for video snapshots and metadata at rest.
- **Non-Repudiation**: Immutable audit logging of all operator overrides, alert dismissals, and policy modifications.
- **Sprint 1 baseline:** no secrets in git, no credentials in API responses or logs, no stack traces in HTTP error bodies.

---

## 8. Multi-Agent Development Workflow

ILKA is developed under a formal multi-agent engineering protocol:

- **Lead Engineering Orchestrator**: [Antigravity] (Scaffolding, architecture enforcement, component planning, verification).
- **Independent Adversarial Reviewer**: [OpenAI Codex] (Challenging implementation decisions, security reviews, edge-case probing per [`CODEX.md`](./CODEX.md)).
- **Interactive Developer**: [Cursor] (In-editor implementation strictly following [`AGENTS.md`](./AGENTS.md)).

---

## 9. Repository Navigation

- [`AGENTS.md`](./AGENTS.md): Binding engineering rules and constitution.
- [`CODEX.md`](./CODEX.md): Adversarial review protocol and severity standards.
- [`CONTRIBUTING.md`](./CONTRIBUTING.md): Step-by-step contribution and testing workflow.
- [`SECURITY.md`](./SECURITY.md): Baseline security architecture and vulnerability policy.
- [`docs/README.md`](./docs/README.md): Documentation index (architecture, ADRs, roadmap).
- [`docs/QUALITY_GATES.md`](./docs/QUALITY_GATES.md): Completeness checklist before merge.
- [`docs/DECISIONS.md`](./docs/DECISIONS.md): APPROVED vs PROVISIONAL vs NOT DECIDED.
- [`.cursor/README.md`](./.cursor/README.md): Cursor rules, skills, and MCP inventory.
