# Intel Mac development setup (ILKA)

Status labels: **IMPLEMENTED** lab paths · **PROVISIONAL** CPU person detector · no CUDA.

This machine profile is **Intel macOS (x86_64)** with Python 3.11. Keep the **main application** and **Computer Vision** environments separate.

Do **not** install Docker for this guide. Do **not** put Torch / OpenCV into the backend `.venv`.

---

## Main application environment

### Backend (`.venv` at repo root)

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/pip install --prefer-binary -e "./backend[dev]"
cp .env.example .env   # if missing; never commit .env
```

Configure Neon (or another Postgres URL) in `.env` only:

- `DATABASE_URL` and/or `ILKA_POSTGRES_URL`
- `AUTH_SECRET_KEY` (local development value; never commit)

```bash
.venv/bin/python scripts/dev/verify_postgres_env.py
.venv/bin/python scripts/dev/alembic_safe.py upgrade head
cd backend && ../.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Checks: http://localhost:8000/health · `/status` · `/ready` · `/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

`VITE_API_BASE_URL` defaults to `http://localhost:8000`.

### Database

Use Neon (`ILKA_POSTGRES_URL` / `DATABASE_URL` in `.env`). Local Homebrew Postgres and Docker Compose are optional and out of scope for this Intel Mac guide.

---

## Computer Vision environment

Use an isolated **pip** venv: `.venv-cv`. Do **not** mix pip Torch with micromamba/conda TorchVision from another channel.

### Why Intel Mac needs different pins

`cv/requirements-detector.txt` targets `torch>=2.4,<2.7`. Official wheels for those versions are **not** published for Intel macOS. On x86_64 Mac use:

```text
cv/requirements-detector-macos-x86_64.txt
```

Pinned pair (CPU-only):

- `torch==2.2.2`
- `torchvision==0.17.2`
- `numpy>=1.26,<2`
- `opencv-python-headless==4.10.0.84`

### Create and install

```bash
python3.11 -m venv .venv-cv
.venv-cv/bin/python -m pip install -U pip
.venv-cv/bin/pip install --prefer-binary -r cv/requirements-detector-macos-x86_64.txt
```

### Verify PyTorch / TorchVision / NMS

```bash
.venv-cv/bin/python -c "import torch; print('Torch:', torch.__version__, 'cuda', torch.cuda.is_available())"
.venv-cv/bin/python -c "import torchvision; print('TorchVision:', torchvision.__version__)"
.venv-cv/bin/python -c "import torch; from torchvision.ops import nms; print(nms(torch.tensor([[0.,0.,10.,10.],[1.,1.,11.,11.]]), torch.tensor([0.9,0.8]), 0.5))"
```

Or run the validator:

```bash
.venv-cv/bin/python scripts/dev/check_cv_environment.py
```

### Model weights (not committed)

Expected local file (after fetch):

```text
data/models/ssdlite320_mobilenet_v3_large_coco.pth
```

Official download name / URL / SHA-256 are pinned in `cv/detectors/person_cpu.py`. Fetch only via:

```bash
.venv-cv/bin/python scripts/dev/fetch_person_detector_weights.py
```

Then set in `.env` (gitignored):

```text
ILKA_CV_PERSON_WEIGHTS=/absolute/path/to/ilka/data/models/ssdlite320_mobilenet_v3_large_coco.pth
```

`CpuPersonDetector` does **not** download weights. A digest mismatch is rejected.

### Run CV tests

```bash
export ILKA_CV_PERSON_WEIGHTS="$(pwd)/data/models/ssdlite320_mobilenet_v3_large_coco.pth"
.venv-cv/bin/python -m pytest -c pytest-cv.ini -v -rs
```

Backend unit tests for CV (mocks / optional OpenCV) still run from `.venv`:

```bash
.venv/bin/python -m pytest tests/unit/test_cv_person_detector.py tests/unit/test_cv_file_source.py -q
```

### Local detection preview

```bash
export ILKA_CV_PERSON_WEIGHTS="$(pwd)/data/models/ssdlite320_mobilenet_v3_large_coco.pth"
.venv-cv/bin/python scripts/dev/preview_person_detection.py \
  --video "data/videos/people-detection (1).mp4" \
  --no-display --no-save --max-frames 30
```

---

## Micromamba note (not part of the active workflow)

If `~/.local/envs/ilka-cv` exists from earlier experiments, leave it alone or delete it yourself later. **ILKA does not use it.** Supported CV workflow is only `.venv-cv` (pip). Mixing micromamba/conda TorchVision with other channels can break `torchvision::nms` on Intel Mac.

---

## Related docs

- [`docs/DEVELOPMENT.md`](../DEVELOPMENT.md) — general local development
- [`cv/README.md`](../../cv/README.md) — lab CV module status
- [`docs/development/migrate-to-new-machine.md`](./migrate-to-new-machine.md) — move checklist
