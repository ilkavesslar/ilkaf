# Requirements

**Status:** **PLANNED** baseline. Nothing **IMPLEMENTED**. Open questions are **NOT DECIDED**.

Authoritative functional list: `docs/requirements/README.md`.

## Product scope (planned)

Industrial/site management, employees, RBAC, cameras and live feeds, PPE/person/unsafe-behavior/restricted-zone detection, incidents, alerts, risk scoring, digital twin, dashboards, notifications, audit logs, reports, AI-assisted analysis, multi-camera, future edge/IoT, production-grade security and observability.

## Documented functional requirements

FR-1 camera management, FR-2 PPE detection, FR-3 restricted zones, FR-4 incident lifecycle, FR-5 real-time alerts, FR-6 HITL verification, FR-7 history/playback.

## Documented non-functional

NFR-1 alert latency (500ms target), NFR-2 UI frame rate, NFR-3 availability 99.9% during plant hours.

## Open questions (`DECISION REQUIRED`)

See `docs/requirements/README.md` section 8: cameras per edge node, Day-1 PPE set, retention, facial blurring mandate, PLC/hardware vs software-only alerts.

NFR-1 (alert latency 500ms) is an **aspirational** goal from the original baseline; it is **not** a validated SLA and is **PROVISIONAL** until measured on real streams.

## Eventual capabilities (incremental, not Phase 1)

Multi-org/tenants, multi-site, PoE multi-camera RTSP, PPE/zone/unsafe-behavior/fall/proximity/vehicle-person, configurable rules, verification, incidents, alerts, ack/escalation, audit, dashboards, reports, analytics, edge AI, hybrid deploy. Camera vendors replaceable via adapters.

Laptop webcams are not the production camera architecture.
