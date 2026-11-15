# ILKA Requirements Baseline Specification

> [!NOTE]
> **Status**: Requirements Engineering Baseline. Items marked with `[OPEN QUESTION]` require formal engineering approval.

---

## 1. Functional Requirements

- **FR-1 (Camera Stream Management)**: The platform shall support onboarding, configuring, and monitoring industrial RTSP/ONVIF camera feeds.
- **FR-2 (PPE Compliance Detection)**: Real-time identification of PPE non-compliance (e.g., hard hats, safety vests).
- **FR-3 (Restricted Zone Monitoring)**: Real-time detection of unauthorized pedestrian intrusion into operator-defined polygon exclusion zones.
- **FR-4 (Incident Generation & Lifecycle)**: Automated generation of candidate safety incidents with state transitions (Triggered → Acknowledged → Verified → Resolved / Dismissed).
- **FR-5 (Real-Time Operator Alerting)**: Sub-second visual and audible alert dispatching to active operator consoles upon hazard detection.
- **FR-6 (Human Verification HITL)**: Workflow enabling human operators to confirm, classify, or reject automated detections.
- **FR-7 (Incident History & Playback)**: Searchable historical repository of safety incidents with synchronized snapshots and metadata.

---

## 2. Non-Functional Requirements

- **NFR-1 (Alert Latency)**: End-to-end latency from frame capture to operator dashboard alert shall not exceed 500ms under standard network conditions.
- **NFR-2 (UI Responsiveness)**: The frontend dashboard shall render live video overlays at a smooth target frame rate (15–30 FPS) without freezing client state.
- **NFR-3 (System Availability)**: The core ingestion and alerting service shall maintain 99.9% uptime during operational plant hours.

---

## 3. Security Requirements

- **SEC-1 (RBAC Enforcement)**: Explicit permission verification on every REST endpoint and WebSocket topic.
- **SEC-2 (Encrypted Transport)**: Mandatory TLS 1.3 for all HTTP, WebSocket, and stream communications.
- **SEC-3 (Zero Hard-Coded Credentials)**: All secret values loaded dynamically via environment variables.
- **SEC-4 (Worker Privacy)**: Data access controls restricting access to video recordings containing worker identifiable information.

---

## 4. AI & Computer Vision Requirements

- **AI-1 (Explainable Metadata)**: Every detection must emit confidence score, bounding box / polygon coordinates, detector model ID, and model version.
- **AI-2 (Configurable Sensitivity)**: Detection confidence thresholds must be configurable per camera zone to minimize false positives.
- **CV-1 (Stream Resiliency)**: Automatic reconnection with exponential backoff on stream disconnection.
- **CV-2 (Frame Rate Adaptation)**: Dynamic frame skipping / drop handling under edge CPU/GPU saturation to avoid unbounded memory buffering.

---

## 5. Hardware & Camera Requirements

- **HW-1 (Camera Protocols)**: Support standard RTSP, RTSPS, and ONVIF Profile S camera streams.
- **HW-2 (Compute Targets)**: Ability to execute inference on standard x86/ARM64 edge nodes (CPU baseline with optional GPU acceleration).

---

## 6. Scalability & Reliability Requirements

- **SCAL-1 (Horizontal Ingestion)**: Ability to partition camera ingestion across multiple edge processes or container instances.
- **REL-1 (Fail-Safe Default)**: Camera disconnects or detector process crashes must immediately trigger high-priority "Monitoring Blind Spot" alerts.

---

## 7. Compliance & Audit Requirements

- **COMP-1 (Immutable Audit Trail)**: Cryptographically verifiable or tamper-evident logging of all operator acknowledgements and supervisor policy modifications.
- **COMP-2 (Exportable Reports)**: Ability to generate standardized safety compliance reports for OSHA / ISO 45001 audits.

---

## 8. Open Questions Requiring Human Lead Approval

- `[OPEN QUESTION 1]`: What is the target number of concurrent RTSP camera streams per edge compute node in the initial deployment?
- `[OPEN QUESTION 2]`: Which specific PPE items (e.g., hard hats, safety vests, protective eyewear, cut-resistant gloves, steel-toed boots) are mandatory for Day 1 MVP vs. Phase 2?
- `[OPEN QUESTION 3]`: What is the required retention duration for video snapshots vs. incident metadata (e.g., 30 days vs. 1 year)?
- `[OPEN QUESTION 4]`: Is automated worker facial blurring legally mandated for the initial deployment facility?
- `[OPEN QUESTION 5]`: Does the platform need to integrate with physical industrial hardware (e.g., Modbus/PLC light towers/relays) or purely software dashboards?
