# AI / CV pipeline

**Status:** Lab path is present for validation (FileSource ingest, `Observation` contract, **PROVISIONAL** CPU person detector). Lab frames and observations stay `[MOCK / SYNTHETIC]`. Independent QA/security review and human closure remain pending. Production readiness and accuracy certification remain open. Production ingest, tracking, PPE, and Detection → Event → Incident → Alert remain **PLANNED**. Frameworks **PROVISIONAL**. A person box is not a completed pipeline.

A raw detector box is **not** an incident.

**Present for lab validation:** local `FileSource`, typed `Observation`, provisional CPU person detection. **PLANNED:** production ingest (RTSP/ONVIF), tracking, PPE, and Detection → Event → Incident → Alert.

## Stages (must stay separate)

```text
Camera stream
  → Ingestion (frames, PTS, camera_id)
  → Processing (decode, optional track)
  → Computer vision models (PPE, person, zone, fall, proximity, …)
  → Observation (probabilistic, versioned model)
  → Detection (thresholded, still not an incident)
  → Event (deduped, temporally persisted, rule-aware)
  → Verification (confidence policy and/or human)
  → Incident (record for operations/compliance)
  → Alert (notify operators)
  → Action / escalation
  → Audit trail
```

| Term | Meaning |
| :--- | :--- |
| Observation | Model output + confidence + geometry + model version + time |
| Detection | Observation that passed a configured threshold |
| Event | Safety-relevant occurrence after persistence, de-dupe, and rules |
| Verification | Automatic policy and/or HITL |
| Incident | Operational case (candidate vs verified states **PLANNED**) |
| Alert | Operator-facing notification |
| Action | Ack, escalate, dismiss, dispatch — audited |

## Controls (required in design)

Confidence thresholds (per camera/zone/rule), temporal persistence (N frames or T seconds), duplicate suppression (track id / spatial hash), configurable rules, HITL for punitive or high-severity paths, escalation timeouts **PLANNED**.

False positives and false negatives are expected. Tune rules; do not “fix” them by collapsing stages.

## Placement

Inference: edge, site server, central, or hybrid. Observations are the integration contract. Model registry/versioning: see [AI_MODELS.md](./AI_MODELS.md).
