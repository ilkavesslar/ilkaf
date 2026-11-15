# Move ILKA to a new machine

This sets up the current lab prototype. It does not enable production cameras or install GPU builds.

The prototype is a modular monolith:

- `backend/` — FastAPI, custom session auth, RBAC, lab camera hub, sampled person preview
- `frontend/` — React and Vite
- `cv/` — frame sources, CPU person detector, anonymous tracking, movement, and waving

## 1. Prerequisites

- Git
- Python 3.11 (the version used by CI)
- Node.js 22 (the version used by CI)
- A PostgreSQL database the app can reach. Local Compose is optional. Neon is configured only through a local `.env`.
- No separate FFmpeg install. RTSP uses the FFmpeg build shipped with OpenCV.
- No GPU. Person detection is CPU Torch. Do not install a CUDA wheel.

Docker is optional and only needed if you start the Compose Postgres service described in `docs/DEVELOPMENT.md`.

## 2. Clone

```powershell
git clone https://github.com/Ebrahim121-1/ilka.git
cd ilka
git checkout feature/sprint-3-rtsp-source
```

Use the branch that contains the lab camera and custom auth work.

## 3. Environment variables

```powershell
Copy-Item .env.example .env
```

Edit `.env` on this machine only. Do not commit it. `.env.example` has empty secrets and the variable names the app reads.

Set at least:

- `AUTH_SECRET_KEY` — long random value. Production requires at least 32 bytes.
- `DATABASE_URL` or, for local development, `ILKA_POSTGRES_URL`
- `ILKA_CV_PERSON_WEIGHTS` — optional if the weights file is at the default path below
- `ILKA_CAMERA_USERNAME` and `ILKA_CAMERA_PASSWORD` — only when a lab camera will be opened
- `ILKA_LAB_CAMERAS_ENABLED=true` — only for a local demo. Leave it `false` until the cameras are reachable. Production refuses lab cameras.

Camera hosts in the template are `192.168.1.13` and `192.168.1.15`. The stable camera IDs remain `vigi-c320i-192.168.1.17` and `vigi-c320i-192.168.1.18`.

## 4. Backend

From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "backend[dev]"
.\.venv\Scripts\python.exe scripts\dev\alembic_safe.py upgrade head
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check: `http://127.0.0.1:8000/health`.

On Windows, open the UI at `http://localhost:5173` so the session cookie matches `http://localhost:8000`. `127.0.0.1` and `localhost` are different sites for that cookie.

The first admin is created with `scripts/dev/bootstrap_admin.py` in a terminal. It prompts for the email and password and does not store them in the command line. Do not run it again if that account already exists.

## 5. CV and AI

Use a second virtual environment. Do not install Torch or OpenCV into `.venv`.

```powershell
py -3.11 -m venv .venv-cv
.\.venv-cv\Scripts\python.exe -m pip install -r cv\requirements-detector.txt
```

Install the CPU Torch wheels from the PyTorch CPU index if the default index would select CUDA. The accepted range is Torch `>=2.4,<2.7` and TorchVision `>=0.19,<0.22`.

OpenCV:

- Server and CI: `opencv-python-headless==4.11.0.86`
- Local windows, including the webcam preview: `opencv-python` at that same version, after uninstalling `opencv-python-headless`

Do not keep both OpenCV distributions in one environment.

Person weights are not in Git. Fetch them with `scripts/dev/fetch_person_detector_weights.py`. The file must match the SHA-256 pin in `cv/detectors/person_cpu.py`. The default location is `data/models/ssdlite320_mobilenet_v3_large_coco.pth`, or set `ILKA_CV_PERSON_WEIGHTS`.

Waving is optional. In `.venv-cv` only:

```powershell
.\.venv-cv\Scripts\python.exe -m pip install mediapipe==0.10.31
```

Place `pose_landmarker_lite.task` at `data/models/pose_landmarker_lite.task`. That file is gitignored. Without MediaPipe or the task file, person detection and movement still run, and waving stays off.

Webcam preview, from the repo root:

```powershell
.\.venv-cv\Scripts\python.exe scripts\dev\preview_webcam_person.py
```

Those frames are `[MOCK / SYNTHETIC]`.

## 6. Frontend

```powershell
cd frontend
npm ci
npm run dev
npm test
npm run build
```

`VITE_API_BASE_URL` defaults to `http://localhost:8000`. Do not put secrets in any `VITE_` variable.

## 7. Cameras

Leave `ILKA_LAB_CAMERAS_ENABLED` false until the PC is on the camera LAN.

Check reachability without printing a URL or a password:

```powershell
Test-NetConnection 192.168.1.13 -Port 554
Test-NetConnection 192.168.1.15 -Port 554
```

The hub opens RTSP with TCP. It keeps one reader per viewed camera and only the latest frame. Detection samples that copy on `ILKA_DETECTION_SAMPLE_INTERVAL_S` (default 2 seconds). The browser MJPEG route is `/api/v1/lab/cameras/{camera_id}/mjpeg` and requires a signed-in session. It never returns the RTSP URL.

## 8. Validation checklist

- [ ] `GET /health` returns healthy
- [ ] `GET /ready` reaches the database
- [ ] Frontend loads at `http://localhost:5173`
- [ ] Sign-in creates an HTTP-only session cookie
- [ ] Webcam preview opens in `.venv-cv`
- [ ] Person weights load and match the pinned digest
- [ ] A person in view produces a bounding box
- [ ] TCP 554 succeeds for both camera hosts before enabling lab cameras
- [ ] `GET /api/v1/detection/observations` returns after a signed-in camera view
- [ ] `/cameras` draws boxes from that response

Unit tests from the repo root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit -q --tb=short
```

Do not treat a skipped CV smoke test as a passed camera test. Live RTSP and a person in frame are physical checks.
