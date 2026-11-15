# Quality gates

A feature is **not complete** until all of the following are done:

1. Requirements understood (and linked or written under `docs/` if new).
2. Architecture impact checked (`docs/ARCHITECTURE.md`, `docs/DECISIONS.md` — no surprise services).
3. Code implemented in the smallest safe change.
4. Unit tests added.
5. Integration tests added where the change touches API/DB.
6. E2E test added for critical user flows (skip with documented reason if UI does not exist yet).
7. Security reviewed (secrets, authz, injection, logging).
8. Database impact checked (migration plan if schema changes).
9. Git diff reviewed (no credentials, no accidental generated junk).
10. Documentation updated.
11. Reviewer: QA/Security in Cursor, then Codex; Claude if architecture/CV/UX is heavy.
12. **Human approval before merge to `main`.**

Do not mark work done if tests were skipped because “there is no runner yet” without recording that gap. After Phase 1 scaffolding, missing tests block completeness.

## Sprint 3 lab CV (lab record; the gates above stay open)

Sprint 3 **M1–M5** implementation is present for lab validation. The bullets below record local results only. Production readiness, accuracy certification, and completion of the gates above remain open. Independent QA/security review (gate 11) and human approval before merge to `main` (gate 12) remain pending.

- Lab CV covers local files only (`FileSource`, Observation, provisional CPU person detector, lab CLI).
- Backend unit tests, local run: **125 passed**, **1 skipped**, **2 warnings**.
- CV unit suite: **62 passed**, **1 warning** (`asyncio_mode` is unknown in `.venv-cv`).
- Isolated smoke: a recorded local run **passed** in **29.50 seconds** before the pinned SHA-256 check. The detector now requires an explicit local file whose digest matches `cv/detectors/person_cpu.py`, and construction does not download weights. Local pytest still skips without that verified file. The GitHub `cv-cpu-smoke` job must execute the smoke; a skip fails the job. This checks the execution path only.
- Preview CLI check: **30** frames, **7** person observations, CPU inference, no output video written. This check is separate from the unreproduced historical 596-frame / 300-observation sample review.
- `[MOCK / SYNTHETIC]` labeling is preserved on FileSource frames and mapped observations.
- RTSP/ONVIF ingestion, PPE detection, incident detection, events, alerts, and the dashboard remain open.
