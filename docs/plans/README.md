# Development Plans & Milestone Roadmap (docs/plans)

> [!IMPORTANT]
> **Status**: Milestone Framework. Detailed sprint plans and task breakdowns will be created following formal human lead approval of the Architecture Review and Technology Choices.

---

## 1. High-Level Development Roadmap

```text
[Phase 0: Engineering Foundation] ──► (COMPLETED)
       │
       ▼
[Phase 1: Architecture Review & Interface Contracts]
       │
       ▼
[Phase 2: Core Ingestion & Computer Vision Engine]
       │
       ▼
[Phase 3: Backend Safety Orchestrator & RBAC]
       │
       ▼
[Phase 4: Operations Dashboard & Real-Time Telemetry]
       │
       ▼
[Phase 5: Quality Assurance, Hardening & Staging Deployment]
```

---

## 2. Milestone Overview

### Phase 0: Engineering Foundation *(Completed)*
- Repository structure initialization.
- Engineering constitution (`AGENTS.md`), Adversarial Reviewer charter (`CODEX.md`), contribution rules, and security baseline.
- Baseline documentation across architecture, requirements, AI/CV, testing, and deployment.

### Phase 1: Architecture Review & Interface Contracts *(Pending Approval)*
- Approval of provisional decisions (FastAPI, Redis Streams, Alembic, WebRTC vs. WebSocket).
- Formalization of OpenAPI contracts, Pydantic schemas, and PostgreSQL DDL migrations.

### Phase 2: Core Ingestion & Computer Vision Engine
- RTSP video stream decoding worker with bounded ring buffers.
- Object & PPE detector wrappers with confidence thresholds.
- Ray-casting zone boundary containment calculations and object tracking.

### Phase 3: Backend Safety Orchestrator & RBAC
- FastAPI application scaffolding with asyncpg database connection pooling.
- Safety incident state machine (Triggered → Acknowledged → Verified → Resolved).
- RBAC middleware and JWT authentication.
- WebSocket real-time event broadcasting service.

### Phase 4: Operations Dashboard & Real-Time Telemetry
- React + TypeScript dashboard with Vite.
- Video stream renderer with dynamic bounding box/polygon overlay.
- Real-time alert feed, audio notifications, and human verification modals.

### Phase 5: Hardening, Benchmarking & Deployment
- Multi-camera load testing and synthetic benchmark execution.
- Independent adversarial audit by Codex per `CODEX.md`.
- Staging environment rollout and operational sign-off.
