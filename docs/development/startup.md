# ILKA developer startup guide

Single workflow for this Intel Mac workspace. Environments stay separate:

| Environment | Path | Purpose |
| :--- | :--- | :--- |
| Backend | `.venv` | FastAPI, DB, auth, API tests |
| Frontend | `frontend/node_modules` | React + Vite |
| CV (lab) | `.venv-cv` | PyTorch, TorchVision, OpenCV, person detector |

Do **not** install Torch into `.venv`. Do **not** use micromamba `~/.local/envs/ilka-cv` for ILKA CV work.

Related detail: [`mac-setup.md`](./mac-setup.md) · [`../DEVELOPMENT.md`](../DEVELOPMENT.md)

---

## First-time setup

### 1. Repository

Clone the official ILKA repository (or initialize Git in this workspace after the readiness checklist), then work on a feature branch. Never commit `.env`, virtualenvs, `node_modules`, or model weights.

### 2. Backend

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install --prefer-binary -e "./backend[dev]"
cp .env.example .env   # if .env does not exist
```

Edit `.env` locally (never commit it):

- `DATABASE_URL` and/or `ILKA_POSTGRES_URL`
- `AUTH_SECRET_KEY`
- optional `ILKA_CV_PERSON_WEIGHTS` after fetching weights

```bash
python scripts/dev/verify_postgres_env.py
python scripts/dev/alembic_safe.py upgrade head
```

### 3. Frontend

```bash
cd frontend
npm install
cd ..
```

### 4. CV (Intel Mac)

```bash
python3.11 -m venv .venv-cv
.venv-cv/bin/python -m pip install -U pip
.venv-cv/bin/pip install --prefer-binary -r cv/requirements-detector-macos-x86_64.txt
.venv-cv/bin/python scripts/dev/fetch_person_detector_weights.py
```

Set in `.env`:

```text
ILKA_CV_PERSON_WEIGHTS=/absolute/path/to/repo/data/models/ssdlite320_mobilenet_v3_large_coco.pth
```

Validate:

```bash
.venv-cv/bin/python scripts/dev/check_cv_environment.py
```

### 5. Pre-flight (all)

```bash
.venv/bin/python scripts/dev/check_development_environment.py
```

---

## Daily development (three terminals)

### Terminal 1 — Backend

```bash
cd /path/to/ilka
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Checks: http://localhost:8000/health · http://localhost:8000/ready · http://localhost:8000/docs

### Terminal 2 — Frontend

```bash
cd /path/to/ilka/frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

UI: http://localhost:5173/

### Terminal 3 — CV

```bash
cd /path/to/ilka
export ILKA_CV_PERSON_WEIGHTS="$(pwd)/data/models/ssdlite320_mobilenet_v3_large_coco.pth"
.venv-cv/bin/python scripts/dev/check_cv_environment.py
.venv-cv/bin/python -m pytest -c pytest-cv.ini -v -rs
```

Optional preview:

```bash
.venv-cv/bin/python scripts/dev/preview_person_detection.py \
  --video "data/videos/people-detection (1).mp4" \
  --no-display --no-save --max-frames 30
```

---

## Do not commit

- `.env`
- `.venv/` / `.venv-cv/`
- `frontend/node_modules/`
- `data/models/*.pth` and other weights
- secrets, connection strings, camera passwords
