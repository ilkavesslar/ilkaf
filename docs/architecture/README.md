# ILKA System Architecture Specification

The diagram below is **aspirational**. Redis Streams and specific detectors are **PROVISIONAL**. Authoritative decisions: [`../DECISIONS.md`](../DECISIONS.md). Pipeline stages: [`../AI-PIPELINE.md`](../AI-PIPELINE.md).

---

## 1. High-Level System Architecture

ILKA is structured as a decoupled, multi-tier industrial edge-and-cloud architecture:

```text
                                  +---------------------------------------+
                                  |       Industrial RTSP/ONVIF Feeds     |
                                  +---------------------------------------+
                                                      │
                                                      ▼
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| cv/ & ai/ Edge Video Ingestion & Vision Processing                                                |
|                                                                                                   |
|  +─────────────────────────+     +─────────────────────────+     +──────────────────────────────+ |
|  | RTSP Stream Ingestion   | ──► | Object & PPE Detectors  | ──► | Spatial Zone & Tracking      | |
|  | (Frame Ring Buffers)    |     | (Bounding Boxes/Polygons)|    | (DeepSORT / ByteTrack)       | |
|  +─────────────────────────+     +─────────────────────────+     +──────────────────────────────+ |
+─────────────────────────────────────────────────┬─────────────────────────────────────────────────+
                                                  │ (Detection Events + Frame Metadata)
                                                  ▼
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| backend/ Core Safety Event Orchestrator                                                           |
|                                                                                                   |
|  +─────────────────────────+     +─────────────────────────+     +──────────────────────────────+ |
|  | Event Ingestion Queue   | ──► | Safety Rules Engine     | ──► | RBAC, Audit & DB Persistence | |
|  | (Redis Stream Buffer)   |     | (Incident Lifecycle)    |     | (PostgreSQL)                 | |
|  +─────────────────────────+     +─────────────────────────+     +──────────────────────────────+ |
+───────────────────────┬─────────────────────────────────────────────────────────┬─────────────────+
                        │                                                         │
                        │ (WebSocket Real-Time Feed)                              │ (REST API)
                        ▼                                                         ▼
+───────────────────────────────────────────────────────────────────────────────────────────────────+
| frontend/ React + TypeScript Operations Dashboard                                                 |
|                                                                                                   |
|  +─────────────────────────+     +─────────────────────────+     +──────────────────────────────+ |
|  | Live Video & Overlays   |     | Real-Time Alert Feeds   |     | Incident Verification (HITL) | |
|  +─────────────────────────+     +─────────────────────────+     +──────────────────────────────+ |
+───────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 2. Component Breakdown

1. **Frontend**: Operations dashboard for operators, safety supervisors, and compliance managers with live telemetry, alert management, and incident verification.
2. **Backend**: Core domain service handling incident state machines, RBAC validation, audit logging, and REST/WebSocket gateways.
3. **Database**: Relational store for users, camera configurations, safety rules, incident histories, and audit records.
4. **Authentication & RBAC**: Central identity enforcement granting fine-grained permissions across all APIs and events.
5. **API Layer**: RESTful interfaces for configuration and management; WebSocket endpoints for real-time telemetry fan-out.
6. **Real-Time Communication**: Push-based event bus streaming safety incidents and telemetry to connected dashboard clients.
7. **Camera Ingestion**: Robust RTSP/ONVIF ingestion workers with backpressure handling, reconnect backoff, and frame decoders.
8. **Computer Vision (CV)**: Real-time object detection, PPE classification, zone boundary crossing calculations, and multi-object tracking.
9. **Artificial Intelligence (AI/ML)**: Anomaly detection, temporal pattern analysis, explainability scoring, and near-miss aggregation.
10. **Event Processing**: High-throughput message queuing and deduplication to decouple detection ingestion from database writes.
11. **Alerting**: Multi-tier alert dispatching (visual, audio dashboard chimes, external sirens/webhooks).
12. **Analytics**: Aggregate reporting on compliance rates, zone hazard frequencies, and peak risk hours.
13. **Logging & Observability**: Centralized structured JSON logging with distributed correlation IDs.
14. **Monitoring**: Prometheus metrics for frame rate, latency, queue depths, and worker health.
15. **Deployment**: Containerized services with edge-to-cloud split topologies.

---

## 3. Technology Decision Matrix

### 3.1 CONFIRMED DECISIONS
- **Frontend Core**: React with TypeScript in strict mode.
- **Backend Language**: Python 3.11+ with strict type hints (`mypy`).
- **Primary Database**: PostgreSQL with relational constraints and indexing.
- **API Contract Standard**: OpenAPI 3.0 / JSON Schemas for REST; typed JSON payloads for WebSockets.
- **Multi-Agent Governance**: Strict compliance with `AGENTS.md` and adversarial review via `CODEX.md`.
- **Human-in-the-Loop Standard**: Safety-critical actions require human operator verification.

### 3.2 PROVISIONAL DECISIONS
- **Backend Web Framework**: FastAPI with `asyncio` and `asyncpg` / `SQLAlchemy 2.0 async`.
- **Message Broker / Cache**: Redis Streams for real-time event decoupling and pub/sub.
- **Computer Vision Framework**: OpenCV + PyTorch / Ultralytics YOLO inference wrapper.
- **Frontend Build Tool**: Vite.
- **Containerization**: Docker & Docker Compose for local development and edge runtime.

### 3.3 DECISIONS REQUIRING APPROVAL
- **Video Streaming Protocol to Browser**: WebRTC vs. Low-Latency HLS (LL-HLS) vs. WebSocket MJPEG/Canvas rendering.
- **Edge Inference Acceleration**: TensorRT / ONNX Runtime vs. standard PyTorch CPU/CUDA execution.
- **Database Migration Tool**: Alembic vs. raw SQL migration runner.
- **Industrial PLC / Hardware Integration**: Selection of physical alarm integration protocols (Modbus, OPC-UA, MQTT vs. software webhooks only).
- **Worker PII Redaction Strategy**: On-edge automated face/plate blurring vs. centralized post-processing redaction.
