# Testing strategy

**Status:** Foundation tests are in place. Sprint 3 **M1–M5** implementation is present for lab validation. Independent QA/security review and human closure gates remain pending. Production readiness, accuracy certification, and the full project quality-gate list remain open. E2E Playwright against a full product is still outstanding.

## Commands

```text
pytest
cd frontend && npm test && npm run build
.\.venv-cv\Scripts\python.exe -m pytest -c pytest-cv.ini -v -rs
```

The last command is the isolated lab CV smoke (separate from the backend `.venv`).

`.github/workflows/ci.yml` runs ruff, SQLite unit tests, a Postgres integration job, and the frontend test/build. The backend job also runs `pytest -c pytest-cv.ini` without Torch, OpenCV, or weights, so that live smoke may skip. The `cv-cpu-smoke` job uses a separate virtualenv, installs the pinned CPU Torch/TorchVision wheels and headless OpenCV, fetches weights through `scripts/dev/fetch_person_detector_weights.py`, sets `ILKA_CV_PERSON_WEIGHTS`, and fails if that smoke test is skipped. The smoke checks pipeline execution and cleanup. It does not certify detection accuracy.

## What is tested now

- `/health` returns 200 with `{"status": "healthy"}` (including empty `DATABASE_URL`) and a request id
- `/status` returns 200 with application, environment, and operational status (no secrets)
- `/ready` against SQLite in-memory; 503 when both `DATABASE_URL` and `ILKA_POSTGRES_URL` are empty; 200 when only `ILKA_POSTGRES_URL` is set (SQLite in unit tests)
- `/ready` against Postgres when `ILKA_POSTGRES_URL` is set (CI service or local `.env` / exported env)
- Alembic upgrade / downgrade / upgrade on Postgres (includes `0003_user_site_assignments`). Head also includes `0005_users_email_lower_unique` (unique index on `lower(email)`); that index has a focused Postgres test and is not a claim that the full downgrade-to-base module was re-run after it
- Production startup refuses missing `DATABASE_URL` even if `ILKA_POSTGRES_URL` is set
- Production startup refuses a missing `AUTH_SECRET_KEY` or an `AUTH_ALGORITHM` list outside the HMAC allowlist
- Error envelope on 404/500 without leaking internals
- Log redaction of secret keys, credential-shaped text in messages, and tracebacks, on both JSON and console formatters; request id, route, exception class, and stable error code stay
- Role names, permission matrix, tenant/site deny; custom-auth session token validation; `/api/v1/me` 401 without a valid token; `/api/v1/auth/login` and `/api/v1/auth/logout` are public and return 501 until implemented; site isolation, foreign-organization 404, and camera metadata authorization; identity resolution by user_id and case-insensitive email; OpenAPI `/api` authentication coverage
- `user_site_assignments` uniqueness and organization isolation
- Frontend `fetchHealth` online/offline handling
- CV `FileSource` / bounded buffer (OpenCV optional; clip tests skip without it)
- CV observation contract: valid payload, invalid confidence/boxes, optional fields, media vs UTC timestamps
- CV person-detector mapping (no Torch/OpenCV): class filter, threshold, clipping, synthetic labels
- CV `CpuPersonDetector` construction/errors with stubs (no weight download). Missing weights, a digest mismatch, and a matching digest are unit-tested. Construction does not open a network connection
- CV live smoke `FileSource → CpuPersonDetector → Observation` skips locally unless OpenCV, CPU Torch/TorchVision, and an `ILKA_CV_PERSON_WEIGHTS` file whose SHA-256 matches the pin are present. Weights are passed explicitly. Zero detections are allowed. The `cv-cpu-smoke` job must execute this test; a skip fails that job
- Backend unit tests, latest local run: **125 passed**, **1 skipped**, **2 warnings**.
- CV unit suite (`.venv-cv`): **62 passed**, **1 warning** (`asyncio_mode` is unknown in `.venv-cv`).
- Isolated smoke (`.venv-cv`, `pytest-cv.ini`): a recorded local run **passed** in **29.50 seconds**, with `ILKA_CV_PERSON_WEIGHTS` pointing at a local weights file. That duration was recorded before the pinned SHA-256 check. The test now skips unless the file matches the pin. It checks the execution path. It is separate from the unreproduced historical 596-frame sample. Accuracy certification remains open. The GitHub `cv-cpu-smoke` job is the path that must not skip.
- CV lab CLI `scripts/dev/preview_person_detection.py`: a missing video or a missing weights file exits non-zero (no weight download). A separate check processed **30** frames, returned **7** person observations, used CPU inference, and wrote no output video.

## Not tested yet

- Playwright journeys and a real identity provider.
- The historical 596-frame / 300-observation sample review. It was not reproduced, and it is separate from the latest 30-frame preview.
- Production readiness, accuracy certification, RTSP/ONVIF ingestion, PPE detection, and incident detection.
- Independent QA/security review and human closure gates for Sprint 3. See [QUALITY_GATES.md](./QUALITY_GATES.md).

Live Neon is validated via `.env` `ILKA_POSTGRES_URL` (never committed). The Postgres job in `.github/workflows/ci.yml` is configured for Compose, not Neon. Authentication tests use in-process HMAC test tokens only.

Quality gates: [QUALITY_GATES.md](./QUALITY_GATES.md).
