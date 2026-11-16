# ADR 0012: Human Intelligence Engine

- **Status:** PROVISIONAL
- **Date:** 2026-11-16
- **Related:** [ADR 0003: Observations are not incidents](./0003-observation-not-incident.md), [ADR 0005: Hybrid / edge inference](./0005-hybrid-edge.md)

## Context

ILKA has working lab components for person detection, camera-local tracking, movement, waving, pose contracts, temporal activity hypotheses, and anonymous cross-camera continuity. These components need one boundary that preserves model provenance, uncertainty, privacy, and the accepted observation-to-incident separation.

The architecture must run on the current Intel Mac CPU development profile without making an unmeasured model change. It must also leave a compatible path for a future NVIDIA profile without introducing a service or Redis.

## Decision

### Placement and flow

The Human Intelligence Engine remains a `cv/` module inside the modular monolith:

```text
Frame
  -> PersonDetector
  -> person Observation
  -> camera-local tracker
  -> optional COCO-17 pose
  -> movement and gesture cues
  -> temporal activity hypothesis
  -> optional anonymous continuity hypothesis
  -> PersonIntelligenceObservation
```

Its output is a probabilistic observation. It is not a detection decision, event, verified identity, incident, alert, or safety determination. Downstream code must preserve the stages in ADR 0003.

### Detector abstraction and runtime profiles

- Detectors implement the existing `PersonDetector` protocol: `model_id`, `model_version`, and `detect(Frame) -> list[Observation]`.
- TorchVision SSDLite320 MobileNetV3-Large through `CpuPersonDetector` remains the default for the `intel_mac_cpu` lab profile until a reproducible, like-for-like evaluation justifies a change.
- YOLO is an optional adapter. Selecting it without its dependency and explicitly pinned local weights must fail closed; the runtime must not download weights or silently substitute another detector.
- The `nvidia_cuda` profile is **PROVISIONAL**. No detector, pose model, throughput, latency, capacity, or accuracy target is selected for it.
- Detector and stage failures must not create positive activity or identity claims. Unavailable optional evidence is represented honestly as missing keypoints, `unknown`, `None`, or a surfaced failure as appropriate.

No benchmark numbers are established by this ADR.

### Tracking and anonymous continuity

- `local_track_id` is camera-session local, produced by the camera-scoped tracker, and must include camera scope. It is an association handle, not a person identity.
- `global_person_id` is an optional, anonymous cross-camera continuity hypothesis. It must remain `None` until assigned and must never be interpreted as a named worker, employee record, or verified identity.
- Ambiguous continuity must create or retain uncertainty rather than force a merge.
- The current matcher is in-memory and uses coarse appearance plus timing/topology evidence. Persistence, retention policy, and distributed matching are not selected by this ADR.

### Pose and temporal activities

- Pose uses exactly 17 joints in COCO-17 order. Coordinates are normalized to `[0, 1]`.
- An unobserved joint has `visibility=0`; coordinates may then be `None`. Missing joints must not be fabricated.
- The temporal activity vocabulary is:
  `standing`, `walking`, `running`, `sitting`, `bending`, `waving`, `falling`, and `person_down`.
- `unknown` is a required ninth enum value for insufficient, unavailable, conflicting, or failed evidence. It must carry activity confidence `0.0`.
- Activities are hypotheses with confidence and temporal state. In particular, `falling` and `person_down` are not incidents and require downstream policy, persistence/de-duplication, and verification.

### Shared contract and versioning

The canonical internal contract is `cv/intelligence/contract.py`:

- `PersonIntelligenceObservation`
- `ActivityClass`
- `Keypoint` and `KeypointName`
- `SCHEMA_VERSION = "1.0.0"`

Every record carries the schema version, UUID observation id, camera/source/time context, local track id, optional global anonymous id, normalized bounding box, detection confidence, 17 keypoints, activity and confidence, optional activity timing, movement state, tracking status, per-stage model versions, and synthetic-data labeling.

Contract versions follow semantic versioning:

- patch: validation or documentation correction that does not change serialized meaning;
- minor: backward-compatible additive change;
- major: removed/renamed fields, changed meaning, changed enum semantics, or another incompatible serialized change.

Consumers must reject unsupported major versions. Producers must not emit undocumented fields or reinterpret existing values without a version change.

### Privacy

- Facial recognition, face embeddings, named identity, gait biometrics, and employee-record linkage are out of scope.
- Global ids must remain anonymous, opaque, and purpose-limited to continuity hypotheses.
- Camera credentials and frames must not be placed in this observation contract or logs.
- Any future biometric identification proposal requires a separate security/privacy review and ADR.

## Consequences

- The engine remains replaceable by stage and deployable at edge, site, central, or hybrid locations through the same observation contract.
- Intel Mac development remains on the measured-in-repo SSDLite path; NVIDIA and alternative-model choices remain open.
- Downstream API, UI, persistence, and event agents have one versioned contract but must not promote observations into incidents.
- Cross-process distribution, durable global identity, model selection, production thresholds, retention, and accuracy certification remain unresolved.

## Provisional acceptance conditions

This ADR may be promoted only after the shared contract is reviewed by CV, backend, frontend, QA/security, and privacy owners; supported runtime profiles have reproducible evaluation records; production thresholds and failure behavior are tested; and retention and access controls for person-intelligence data are decided.
