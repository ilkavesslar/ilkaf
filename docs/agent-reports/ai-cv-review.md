# Sprint 0.5 AI/CV review (no camera work)

Foundation remains **not** camera-ready, which is correct. Sprint 0.5 did not add RTSP, detectors, or models.

## Ready later

- Modular `cv/` still empty — ingest can attach without a new service (ADR 0001).
- Observation ≠ incident still documented (ADR 0003).
- UI cameras page is a placeholder.

## Blockers before ingest

1. Camera registry + secret references (no plaintext RTSP in DB/git).
2. Real authentication so camera metadata is tenant-scoped (`require_organization` exists; login does not).
3. Health taxonomy: camera unavailable vs API `/health`.
4. Do not put decode/inference in `frontend/`.

**Not READY for Sprint 1 cameras** until OIDC login exists and Postgres/Neon ops are human-verified.
