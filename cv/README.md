# Computer Vision Subsystem (cv)

**Status:** Sprint 3 **M1–M5** implementation is present for lab validation. Independent QA/security review and human closure gates remain pending. Production readiness, accuracy certification, and the full project quality-gate list remain open.

- **M1** — `FileSource` and a bounded frame buffer.
- **M2** — typed `Observation` / `BoundingBox` contract.
- **M3** — optional CPU person detector (**PROVISIONAL** lab adapter; not the production model ADR).
- **M4** — **PROVISIONAL** lab CLI `scripts/dev/preview_person_detection.py` (`FileSource` → `CpuPersonDetector` → `Observation`; OpenCV window or annotated MP4).
- **M5** — quality/unit tests, isolated CV smoke, and lab-evidence documentation.

There is no backend or HTTP CV API. `RtspSource` is a provisional lab adapter and is not production camera integration. Webcam, ONVIF, tracking, PPE, and incidents are outside this module.

All M1 frames are labeled **`[MOCK / SYNTHETIC]`**. This is not factory CCTV. File-sourced M3 observations keep that label.

OpenCV is an **optional** dependency used by `FileSource` and `RtspSource`. Torch / TorchVision are **optional** dependencies used only by `CpuPersonDetector`. The FastAPI backend and Sprint 0–2 tests do not require them. Unit tests mock RTSP capture and do not open a network stream. The opt-in localhost smoke test below is separate and skips unless `ILKA_RTSP_SMOKE_URL` is set.

```powershell
pip install opencv-python-headless
```

`opencv-python-headless` is the server and CI package. Its build has no desktop GUI. RTSP ingest and the file smoke job stay on that package. A local webcam window needs the GUI build of the same OpenCV version, with the headless package removed so the two distributions do not conflict:

```powershell
python -m pip uninstall -y opencv-python-headless
python -m pip install "opencv-python==<same version>"
```

The local waving preview also uses MediaPipe pose wrists. Install `mediapipe==0.10.31` in `.venv-cv` only. It must not replace NumPy, Torch, TorchVision, or OpenCV. Place the lite pose model at `data/models/pose_landmarker_lite.task`. That file stays out of git with the other model weights. Without it, movement labels still run and waving stays off.

Do **not** `pip install -r cv/requirements-detector.txt` into the backend environment. Use the isolated CPU venv in the smoke section below.

Install **CPU** PyTorch wheels from the CPU index. Do not install CUDA builds. M3 never selects CUDA.

## Isolated CPU smoke environment

Ordinary `pytest` does **not** download weights and skips live inference. Use a separate venv:

```powershell
python -m venv .venv-cv
.\.venv-cv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install pytest opencv-python-headless
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python scripts/dev/fetch_person_detector_weights.py
$env:ILKA_CV_PERSON_WEIGHTS = "$(Get-Location)\data\models\ssdlite320_mobilenet_v3_large_coco.pth"
python -m pytest -c pytest-cv.ini -q
python scripts/dev/bench_cpu_person_detector.py
python scripts/dev/preview_person_detection.py --video "data/videos/people-detection (1).mp4" --no-display --no-save --max-frames 30
```

**Intel macOS (x86_64):** use `cv/requirements-detector-macos-x86_64.txt` (torch 2.2.2 + torchvision 0.17.2). See [`docs/development/mac-setup.md`](../docs/development/mac-setup.md). Validate with `scripts/dev/check_cv_environment.py`. Do not mix micromamba/conda TorchVision with a second pip install.

`pip install -r cv/requirements-detector.txt` from default PyPI can install a CUDA wheel; prefer the CPU index above (or the Intel Mac pin file on x86_64).

The preview command above uses the same bounds as the verified check: no window, no output file, 30 frames. Omitting `--no-save` writes `data/videos/people-detection-annotated.mp4`. `bench_cpu_person_detector.py` requires `ILKA_CV_PERSON_WEIGHTS` and does not download weights. `CpuPersonDetector` loads only that explicit local file, and only after its SHA-256 matches the pin in `cv/detectors/person_cpu.py`.

The smoke test generates a short temp MJPG clip (not committed). Zero person boxes is allowed. It is not a quality or real-time benchmark.

### Closeout smoke (verified)

Isolated environment (not the backend venv):

```powershell
.\.venv-cv\Scripts\python.exe -m pytest -c pytest-cv.ini -v -rs
```

A recorded local run **passed** in **29.50 seconds** before the pinned SHA-256 check. Test: `tests/cv_ai/test_cv_file_person_smoke.py::test_file_source_cpu_person_detector_smoke`. The test now skips unless OpenCV, CPU Torch/TorchVision, and an `ILKA_CV_PERSON_WEIGHTS` file matching the pin are present. It checks the **FileSource → CPU person detector** path on a generated temporary clip, including source cleanup. It does not certify accuracy. This result is separate from the unreproduced historical 596-frame sample. The GitHub `cv-cpu-smoke` job must execute the test; a skip fails that job.

## M5 quality / validation

M5 is tests and evidence, not a new detector. Latest verified CV unit suite: **62 passed**, **1 warning** (`asyncio_mode` is unknown in `.venv-cv`). Unit tests cover CLI missing paths, FileSource `source_id`, and mapping boxes. Isolated smoke is recorded above and skips without optional CPU dependencies or an explicit weights file. A separate preview CLI check processed **30** frames, returned **7** person observations, ran CPU inference, and wrote no output video. FileSource frames and CV observations stay **`[MOCK / SYNTHETIC]`**. This records lab validation. Independent QA/security review and human closure gates remain pending.

## M4 lab CLI (not a product API)

`scripts/dev/preview_person_detection.py` is the M4 hook: argparse over local files only. It does not start FastAPI, write to Postgres, or emit events. Use `.venv-cv`. It never downloads weights (`--weights` / `ILKA_CV_PERSON_WEIGHTS` must already be a file).

## Lab evidence (one sample, not a metric)

The latest verified preview check processed **30** frames of `data/videos/people-detection (1).mp4` and returned **7** person observations on CPU, with no output video written. An older note cited **596** frames and **300** person observations for that file. That sample review was not reproduced. The 30-frame check and the 596-frame note are separate samples. They are not precision/recall scores. Production readiness, accuracy certification, production RTSP/ONVIF ingestion, PPE detection, and incident detection remain open. FileSource frames and mapped observations stay **`[MOCK / SYNTHETIC]`**. The provisional RTSP adapter is covered under [RTSP lab verification](#rtsp-lab-verification).

## What exists

```text
cv/
├── frame.py
├── observation.py
├── errors.py
├── opencv.py               # Optional cv2 loader
├── detectors/
│   ├── base.py             # PersonDetector protocol
│   ├── mapping.py          # Pixel boxes → M2 Observation (no Torch)
│   └── person_cpu.py       # SSDLite320 MobileNetV3-Large, CPU only
└── streams/
    ├── base.py
    ├── buffer.py
    ├── file.py
    └── rtsp.py             # Provisional RTSP adapter
```

`Observation.media_timestamp` is optional source/media time (`Frame.captured_at`). `Observation.observed_at` is UTC wall-clock processing time (`Frame.processed_at`). `FileSource(timeline_origin=...)` must be timezone-aware; naive values are rejected.

`is_synthetic` and `mock_label` are normalized together (`normalize_mock_label`).

M3 `min_confidence` default is **0.25 inclusive**. It is noise suppression on the adapter, not the pipeline Detection / Event / Incident stages (ADR 0003).

## M3 weights (do not commit)

- Model: TorchVision **SSDLite320 MobileNetV3-Large**, COCO pretrained (`SSDLite320_MobileNet_V3_Large_Weights.COCO_V1`). This remains a provisional lab adapter.
- Official artifact: `https://download.pytorch.org/models/ssdlite320_mobilenet_v3_large_coco-a79551df.pth`.
- Pinned SHA-256: `a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2` (14,069,355 bytes). PyTorch publishes the leading eight hex characters in the filename. The full digest was taken from that official URL after the prefix and catalog size matched. It is not a separate checksum file published by PyTorch.
- `scripts/dev/fetch_person_detector_weights.py` downloads that URL and saves the file only when the size and digest match.
- Set `ILKA_CV_PERSON_WEIGHTS` or pass `weights_path`. Construction does not download weights. A missing path, an unreadable file, or a digest mismatch raises `DetectorModelError` before the state dictionary is loaded. Live tests skip unless the configured file matches the pin. The file smoke test passes `weights_path` explicitly.

Observations are **not** incidents, alerts, or events (ADR 0003).

## RTSP lab verification

`RtspSource` implements the `VideoSource` protocol for `rtsp` and `rtsps` URLs. It is a provisional lab adapter. It is not ONVIF, not a camera-unavailable event, and not production camera integration.

Mocked unit tests (no socket) verify configuration bounds, credential-free `source_id` values, OpenCV timeout properties, real `Frame` metadata (`source_kind="rtsp"`, `is_synthetic=False`, empty `mock_label`), NumPy buffer copies, bounded reconnect with `retry_delay_s`, and repeated `close()`. A dead RTSP read raises. It does not return `None` and it does not substitute a synthetic frame. `None` remains the file-source end of stream.

Localhost smoke, recorded 2026-10-18, used MediaMTX v1.21.2 on `127.0.0.1:18554` only and FFmpeg `testsrc` at 320×240. Those pixels are **`[MOCK / SYNTHETIC]`** test patterns, not factory footage. The client set `OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp` because `RtspSource` does not choose UDP or TCP. `.venv-cv` has OpenCV 5.0.0.

```powershell
.\.venv-cv\Scripts\python.exe -m pytest tests/cv_ai/test_cv_rtsp_smoke.py -q --tb=short -rs
```

That command **passed**: **1 passed**, **1 warning** (`asyncio_mode` is unknown in `.venv-cv`), **7.43s**. Frames were `uint8` arrays shaped `(240, 320, 3)`. `close()` ran twice, and a second open read another frame. A separate live check restarted the publisher and the already-open source returned another `(240, 320, 3)` frame after reconnect (`source_kind="rtsp"`, index 1).

`is_synthetic=False` means the adapter classified the transport as RTSP. It does not mean the `testsrc` pixels are a real camera.

Not verified: a physical TP-Link VIGI camera. No host, stream path, or credential variable is configured in this environment. An OpenCV probe to the documentation address `192.0.2.1` with a 1500 ms open timeout returned `isOpened() == False` in about 2.75 s and did not print the URL. That checks the timeout property only.

Repeat the smoke only against loopback. The stock MediaMTX config listens on all interfaces and allows anonymous publish; do not start that for this test. Keep the URL free of userinfo. The test skips when `ILKA_RTSP_SMOKE_URL` is unset and fails closed if the URL contains `@`.

## Planned (not M1–M5)

```text
cv/
├── streams/                # FileSource; provisional RtspSource; webcam later
├── detectors/              # PPE and other classes later
├── tracking/
└── utils/
```
