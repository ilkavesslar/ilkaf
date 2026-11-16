# Human Intelligence Engine

**Status:** **PROVISIONAL** lab architecture and implementation. It emits probabilistic observations, not incidents or verified identities. Production accuracy, model selection, persistence, retention, and capacity are not certified.

Canonical decision: [ADR 0012](./DECISIONS/0012-human-intelligence-engine.md).

## Purpose and boundaries

The engine turns person observations from one camera frame into versioned, per-track human-intelligence observations. It composes existing CV stages inside the modular monolith; it is not a new service and does not require Redis.

It does not perform facial recognition, identify named people, confirm incidents, or guarantee physical safety.

## Data flow

```text
FileSource / RtspSource
  -> Frame
  -> PersonDetector
  -> person Observation
  -> CameraScopedTracker
  -> optional PoseEstimator (COCO-17)
  -> movement + wave cues
  -> TemporalActivityRecognizer
  -> optional AnonymousIdentityMatcher
  -> PersonIntelligenceObservation (schema 1.0.0)
  -> downstream observation/detection/event/verification stages
```

Failure and absence are data:

- no pose model or a pose-stage failure produces 17 unobserved keypoints;
- insufficient temporal evidence produces `activity_class=unknown` and confidence `0.0`;
- an unconfirmed local track has no global id;
- optional appearance failure creates no identity evidence;
- detector selection or inference failure is surfaced and must not become a positive observation.

## Shared observation contract

`cv/intelligence/contract.py` is the canonical internal contract. `SCHEMA_VERSION` is `1.0.0`.

`PersonIntelligenceObservation` contains:

- record context: `observation_id`, `schema_version`, `camera_id`, `source_id`, optional `frame_id`, and timezone-aware `timestamp`;
- tracking: camera-local `local_track_id`, optional anonymous `global_person_id`, and `tracking_status`;
- measured evidence: normalized `bbox`, `detection_confidence`, exactly 17 COCO-ordered keypoints, and `movement_state`;
- temporal hypothesis: `activity_class`, `activity_confidence`, and optional activity start/duration;
- provenance: detector, tracker, pose, activity, and identity versions in `model_versions`;
- data origin: `is_synthetic` and `mock_label`.

The activity vocabulary has eight positive hypotheses:

`standing`, `walking`, `running`, `sitting`, `bending`, `waving`, `falling`, and `person_down`.

`unknown` is also mandatory. Consumers must handle it and must not coerce it into a positive activity.

### Track identifiers

- `local_track_id` is scoped to one camera tracker session and currently has the form `{camera_id}:t{number}`. It is not stable across process restart and is not identity.
- `global_person_id` is an optional opaque `gp-...` continuity hypothesis. It is anonymous, may be absent, and must never be joined to employee identity as though verified.
- Matching uncertainty must not be hidden. A global id does not prove that two tracks are the same real-world person.

### Contract evolution

Serialized contract changes use semantic versioning. Backward-compatible additions require a minor version; incompatible field or enum changes require a major version. Consumers must reject unsupported major versions. Every producer must include stage provenance and preserve synthetic-data labels.

## Runtime profiles

### Intel Mac CPU

**IMPLEMENTED / PROVISIONAL lab profile**

- `.venv-cv` pins Torch `2.2.2` and TorchVision `0.17.2`.
- `CpuPersonDetector` with SSDLite320 MobileNetV3-Large is the default.
- Weights are local and integrity-pinned; runtime model selection must not download weights.
- No production accuracy, latency, throughput, or camera-capacity claim is made.

SSDLite remains the default until a reproducible evaluation on the same inputs, thresholds, and machine profile justifies replacement.

### NVIDIA CUDA

**PROVISIONAL / PLANNED**

- The deployment profile is allowed by the hybrid architecture.
- No production detector, pose model, model weights, hardware size, or performance target is selected.
- YOLO is optional and not the default. Missing dependency or local weights must fail closed, without silent fallback or runtime download.

## Module map

| Module | Status | Responsibility |
| :--- | :--- | :--- |
| `cv/detectors/base.py` | **IMPLEMENTED** | Detector protocol returning person observations |
| `cv/detectors/person_cpu.py` | **IMPLEMENTED / PROVISIONAL** | Intel Mac CPU SSDLite lab adapter |
| `cv/detectors/registry.py` | **IMPLEMENTED** | Named selection, availability, SSDLite default |
| `cv/detectors/yolo_optional.py` | **IMPLEMENTED / PROVISIONAL** | Optional YOLO adapter; dependency and weights required |
| `cv/intelligence/contract.py` | **IMPLEMENTED** | Schema `1.0.0`, COCO-17, activity and tracking contracts |
| `cv/intelligence/tracker.py` | **IMPLEMENTED / PROVISIONAL** | Camera-local IoU/center association and track lifecycle |
| `cv/pose/coco17.py` | **IMPLEMENTED** | Pose protocol, COCO-17 representation, track association |
| `cv/pose/mediapipe_adapter.py` | **IMPLEMENTED / PROVISIONAL** | Optional pose adapter; not a selected production model |
| `cv/movement.py` | **IMPLEMENTED / PROVISIONAL** | Track-centre movement heuristic |
| `cv/gestures.py` | **IMPLEMENTED / PROVISIONAL** | Anonymous wrist-motion wave heuristic |
| `cv/activity/temporal.py` | **IMPLEMENTED / PROVISIONAL** | Stateful eight-class activity hypotheses plus `unknown` |
| `cv/identity/anonymous.py` | **IMPLEMENTED / PROVISIONAL** | In-memory anonymous continuity hypotheses |
| `cv/intelligence/engine.py` | **IMPLEMENTED / PROVISIONAL** | Per-camera composition and fail-safe degradation |
| Persistent/API event integration | **PLANNED** | Observation storage and later detection/event/verification stages |
| Production model certification | **PLANNED** | Dataset approval, accuracy, reliability, and capacity evidence |

## Acceptance criteria mapping

| Criterion | Evidence and status |
| :--- | :--- |
| Detector implementation can be replaced without changing the engine contract | `PersonDetector` protocol and registry — **IMPLEMENTED** |
| Intel Mac has an explicit default | SSDLite via `CpuPersonDetector` — **IMPLEMENTED / PROVISIONAL** |
| Optional YOLO cannot silently weaken configuration | Explicit adapter requirements and fail-closed construction/inference — **IMPLEMENTED** |
| Tracks cannot collide across cameras | Camera-scoped tracker ids — **IMPLEMENTED** |
| Cross-camera continuity is distinguishable from identity | Nullable opaque `global_person_id` and anonymous matcher — **IMPLEMENTED / PROVISIONAL** |
| Pose shape and ordering are stable | Exactly 17 COCO-order keypoints, missing values represented explicitly — **IMPLEMENTED** |
| All required activities are representable | Eight hypotheses plus mandatory `unknown` — **IMPLEMENTED** |
| Activity claims use temporal evidence and uncertainty | Stateful recognizer, confidence, start time, and duration — **IMPLEMENTED / PROVISIONAL heuristics** |
| Every result is versioned and traceable | Schema `1.0.0` plus per-stage `model_versions` — **IMPLEMENTED** |
| Synthetic input cannot be presented as real | `is_synthetic` and normalized mock label — **IMPLEMENTED** |
| Facial or named identification is excluded | No face pipeline or employee linkage; architecture prohibition — **PROVISIONAL decision** |
| Observation cannot be treated as an incident | ADR 0003 stage boundary and engine contract — **APPROVED boundary / IMPLEMENTED output** |
| Production quality is supported by measured evidence | Dataset approval, accuracy, thresholds, hardware capacity, and field validation — **PLANNED** |

## Operational and privacy requirements

- Isolate one camera failure from other camera engines.
- Preserve UTC timestamps, camera scope, confidence, geometry, and model provenance.
- Never log camera credentials, frames, appearance signatures, or employee data.
- Treat `falling` and `person_down` as unverified hypotheses. Downstream persistence, de-duplication, policy, and HITL requirements still apply.
- Restrict access and define retention before persisting person-intelligence observations or anonymous continuity state.
- A missing stream or failed model is degraded monitoring, not evidence that no safety event occurred.

## Open decisions

- Production detector and pose models for Intel and NVIDIA profiles.
- Approved evaluation datasets and acceptance thresholds.
- Persistence, retention, deletion, and access-control policy.
- Cross-process or multi-node continuity; the current matcher is in-memory only.
- API and database representation for this contract.
- Production camera capacity and edge hardware sizing.
