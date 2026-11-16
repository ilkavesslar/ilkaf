# Human Intelligence Engine — security & privacy review

**Date:** 2026-11-16  
**Scope:** HIE CV contract, live preview API mapping, frontend overlays, training docs.

## Controls preserved or added

- Anonymous IDs only (`local_track_id`, optional `global_person_id`). No facial recognition. No employee name inference.
- Live API mapping strips secrets (no RTSP URLs, credentials, model paths in `LiveObservationItem`).
- Existing session auth / RBAC remains the only auth path for detection endpoints.
- `.gitignore` continues to exclude `.env`, `*.pt` / `*.pth` / `*.onnx`, weights, local venvs, `node_modules`.
- Dataset manifests record license status; download scripts must not fetch restricted corpora.
- Synthetic / mock frames keep `[MOCK / SYNTHETIC]` labeling through the HIE contract.

## Residual risks / follow-ups

- Camera credentials still come from environment / encrypted store; operators must not paste them into tickets or logs.
- Global anonymous association audit UI is minimal; operators need a later correction workflow before production identity continuity claims.
- Retention policy for observation history is **NOT DECIDED** (use existing product retention ADRs when persistence lands).
- Pose overlays can reveal body posture; treat live views as sensitive industrial video under existing SECURITY-ARCHITECTURE rules.
