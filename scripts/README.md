# Engineering & Automation Scripts

This directory is for developer and CI helpers (environment checks, safe Alembic, lab CV tooling).

Sprint 3 **lab** scripts (not backend runtime):

- `scripts/dev/fetch_person_detector_weights.py` — downloads the official SSDLite artifact into `data/models/` and writes it only when the size and pinned SHA-256 match. A mismatch deletes the partial file and exits non-zero.
- `scripts/dev/bench_cpu_person_detector.py` — optional CPU latency printout. It requires `ILKA_CV_PERSON_WEIGHTS` and does not download weights. The detector rejects a file whose digest does not match the pin.
- `scripts/dev/preview_person_detection.py` — lab FileSource preview with person boxes (OpenCV window or annotated MP4)

Foundation helpers:

- `scripts/dev/verify_postgres_env.py` — confirms `ILKA_POSTGRES_URL` is set without printing it
- `scripts/dev/alembic_safe.py` — runs Alembic with redacted output (Settings / `.env`, no python-dotenv)
- `scripts/dev/check_cv_environment.py` — validates isolated CV interpreter (Torch, TorchVision NMS, OpenCV, weights); does not touch the database
- `scripts/dev/check_development_environment.py` — pre-flight for `.venv`, `.venv-cv`, `.env` keys (no secret values), Node, weights; report-only

## Directory Layout (Planned)

```text
scripts/
├── dev/                    # Env checks, safe Alembic runner, local helpers
└── setup/                  # Environment check, pre-commit hook installer
```
