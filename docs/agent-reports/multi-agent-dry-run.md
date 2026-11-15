# Multi-agent dry-run: first PoE IP camera ingestion pipeline

**Date:** 2026-08-20  
**Task:** Evaluate architecture for adding the first PoE IP camera ingestion pipeline. **Do not implement.**  
**Status of code:** `cv/` **SCAFFOLDED** only.

## Objective

Decide where ingest belongs, what to build later, security/tests, and AI/CV constraints — without writing a stream client.

## Files inspected

`docs/SYSTEM-ARCHITECTURE.md`, `CAMERA-ARCHITECTURE.md`, `AI-PIPELINE.md`, `EVENT-ARCHITECTURE.md`, `SECURITY-ARCHITECTURE.md`, `DATABASE-ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `ROADMAP.md`, `DECISIONS/0001`–`0006`, `cv/README.md`, `ARCHITECTURE.md`.

## Files changed

None (dry-run).

---

## Architect

**What:** First ingest path for **PoE IP / RTSP** cameras (ONVIF optional later). Not laptop webcams.

**Where:** `cv/` adapter module called from the **same** backend process (ADR 0001). No camera microservice.

**Interfaces (later):** Camera registry (id, site, secret-ref for RTSP, health); adapter: connect / disconnect / last-frame UTC / error class; emit **observations** only — not incidents (ADR 0003).

**Dependencies:** Phase 1 identity/org/site/audit should exist first ([ROADMAP.md](../ROADMAP.md) Sprint 1–2). FastAPI **PROVISIONAL**. No Redis (ADR 0006). Browser playback **NOT DECIDED** (P8).

**Security:** RTSP password in secret store, not git/logs; `organization_id` + `site_id`; view/export audited when UI exists.

**Test:** Fake RTSP or file source labeled `[MOCK / SYNTHETIC]`; reconnect/backoff; camera-unavailable after threshold; no production cameras in CI.

**Conflict:** Roadmap Sprint 3 is registry-only; ingest is Sprint 4. Doing ingest first would skip tenancy/audit.

---

## Builder (no code)

Required later, in order:

1. Persistence: `camera` + secret reference (not plaintext URL in git).  
2. `cv/` process: one adapter implementation, bounded buffer, reconnect.  
3. Health API: camera unavailable vs system down.  
4. Tests with mock source.  
5. Do **not** add Redis, Kubernetes, YOLO, or WebRTC until ADRs say so.

Touched modules when built: `database/`, `backend/` (registry + health), `cv/streams/`, tests. `frontend/` optional (status pill only).

---

## AI/CV

Ingest ≠ detection. First pipeline may stop at **frames + health**. When models exist: observation → event → verified → incident → alert. Need FPS/latency budget, per-camera isolation, timestamps/clock skew, edge vs central later (ADR 0005). Lighting/occlusion/FP/FN apply only once a detector exists. Do not select a model family now (N6).

---

## QA/Security

| Severity | Issue | Why | Test later |
| :--- | :--- | :--- | :--- |
| CRITICAL | RTSP credentials in repo, logs, or API responses | Credential theft, plant video access | Secret-scan CI; log redaction tests |
| HIGH | Ingest without tenant/site scope | Cross-site video | Authz tests on camera APIs |
| HIGH | Silent disconnect | Operators think floor is monitored | Health = unavailable after N seconds |
| HIGH | Skipping HITL / collapsing to incident | False punitive actions | Pipeline contract tests |
| MEDIUM | Unbounded frame queue | OOM, process death | Buffer cap unit test |
| MEDIUM | Mock webcam treated as production | Wrong architecture | Config flag + `[MOCK / SYNTHETIC]` |
| LOW | No ONVIF in v1 | Ops friction | Document gap |
| INFO | Playwright cannot test RTSP | E2E only health UI | API/unit for ingest |

Reliability: reconnect, disk full, CPU peg, DB down while streaming (drop vs backpressure — **NOT DECIDED**).

---

## Conflicts

1. **`develop` vs `development`** — use `develop` until ADR.  
2. **Ingest now vs roadmap** — registry after auth; ingest after registry.  
3. **Historical Redis diagram** vs ADR 0006 — Postgres/in-process first.  
4. **NFR-1 500ms** vs unmeasured RTSP+decode — treat as aspirational.

## Missing architecture

Exact adapter interface types; secret-manager choice; recording/retention; ONVIF profile set; playback protocol; drop-vs-block when DB is down.

## Unresolved decisions

P1 FastAPI, P10 migrations, N3 auth, N5 camera SKU, P8 playback, ingest backpressure policy.

## Decisions (this dry-run)

No implementation. Follow ADRs 0001–0006. First **code** remains Sprint 1 (org/user/site/audit), not ingest.

## Tests

None run (no ingest code).

## Risks

Building RTSP before tenancy; leaking URLs; treating mock webcam as prod.

## Recommended next action

Human: GitHub + Neon dev + accept FastAPI/migrations. Then Sprint 1 identity slice. Camera ingest only after registry sprint.
