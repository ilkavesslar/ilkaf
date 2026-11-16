# Human Intelligence Engine architecture report

## Objective

Define a provisional, implementation-aligned architecture for ILKA person intelligence without creating a service, choosing unmeasured production models, introducing facial recognition, or collapsing observations into incidents.

## Files inspected

- `docs/ARCHITECTURE.md`
- `docs/AI-PIPELINE.md`
- `docs/CAMERA-ARCHITECTURE.md`
- `docs/REQUIREMENTS.md`
- `docs/DECISIONS.md`
- `docs/DECISIONS/0003-observation-not-incident.md`
- `docs/DECISIONS/0005-hybrid-edge.md`
- `docs/models/HUMAN_INTELLIGENCE_MODELS.md`
- `cv/detectors/`
- `cv/intelligence/`
- `cv/pose/`
- `cv/activity/temporal.py`
- `cv/identity/anonymous.py`
- `cv/movement.py`
- `cv/gestures.py`
- related unit tests under `tests/unit/`

## Files changed

- `docs/DECISIONS/0012-human-intelligence-engine.md`
- `docs/HUMAN-INTELLIGENCE.md`
- `docs/DECISIONS.md`
- `docs/agent-reports/human-intelligence-architecture.md`

## Decisions

- Keep the engine in `cv/` within the modular monolith.
- Preserve `PersonDetector` as the detector boundary.
- Keep SSDLite as the Intel Mac CPU default until measured evidence supports replacement.
- Keep YOLO optional and fail closed when its runtime or pinned local weights are unavailable.
- Define the NVIDIA CUDA profile as provisional, with no selected model or invented capacity target.
- Standardize pose on COCO-17 and activities on eight positive hypotheses plus required `unknown`.
- Separate camera-local tracking from optional global anonymous continuity.
- Prohibit facial recognition, biometric templates, named identity, and employee-record linkage.
- Canonicalize the current internal serialized contract as version `1.0.0`.
- Preserve ADR 0003: all Human Intelligence Engine results are observations, not incidents.

## Shared contracts other agents must follow

### CV agents

- Implement detectors through `PersonDetector`; return `Observation` values with confidence, geometry, camera/time context, and model provenance.
- Do not change SSDLite as the Intel Mac default without a reproducible like-for-like evaluation and an architecture decision update.
- Do not download weights at runtime. Explicit YOLO selection with missing requirements must fail closed.
- Emit exactly 17 COCO-order keypoints. Represent unavailable joints honestly; never synthesize coordinates.
- Keep all eight positive `ActivityClass` values and `unknown`. `unknown` must have confidence `0.0`.

### Backend and persistence agents

- Treat `PersonIntelligenceObservation` schema `1.0.0` as the current contract.
- Preserve UUID, UTC timestamp, camera/source scope, local/global id distinction, bounding box, confidence, keypoints, activity timing, movement/tracking status, model versions, and synthetic labels.
- Reject unsupported major schema versions. Do not reinterpret or rename fields without versioning.
- Do not persist person-intelligence or continuity data until access and retention policy are defined.
- Do not promote an observation directly to an incident; use the accepted detection/event/verification stages.

### Frontend agents

- Label activities as model hypotheses, not confirmed facts.
- Handle `unknown`, absent pose, absent global id, and degraded stages as normal states.
- Never display `global_person_id` as a worker identity or imply facial recognition.
- Preserve `[MOCK / SYNTHETIC]` labeling where source data is synthetic.

### QA and security agents

- Test unsupported schema versions, enum completeness, missing keypoints, `unknown` confidence, camera isolation, detector/pose failures, ambiguous identity matching, and synthetic labels.
- Verify camera credentials, frames, appearance signatures, and employee data are absent from contract logs.
- Reject any face, gait-biometric, named-identity, or employee-linkage expansion without a separate privacy/security ADR.
- Verify falling/person-down output cannot bypass persistence, de-duplication, policy, and verification.

## Tests

Documentation-only architecture change. Existing implementation and unit tests were inspected for contract alignment; no benchmark or production-readiness claim was created. Documentation links and the final diff should be checked before handoff.

## Unresolved issues

- Production model selection and acceptance thresholds.
- Approved datasets and legal/privacy basis for evaluation.
- NVIDIA model and hardware profile.
- Persistence, retention, deletion, and access controls.
- Multi-process continuity and camera-topology configuration.
- API and database contracts downstream of the internal CV record.

## Risks

- Consumers may mistake a global anonymous id for verified identity.
- Rule-based activity confidence may be shown as operational certainty.
- An optional model may be selected without its dependencies, pinned weights, or evaluation record.
- Future serialization changes may bypass semantic versioning.
- Persistence before retention and authorization decisions could create unnecessary sensitive data.

## Recommended next action

Have Builder and AI/CV agents verify their code and tests against the shared contracts, then have QA/Security review privacy boundaries and failure behavior before any API or persistence integration.
