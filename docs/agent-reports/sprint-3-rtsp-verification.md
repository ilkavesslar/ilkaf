# Sprint 3 RTSP verification

**Branch:** `feature/sprint-3-rtsp-source`  
**Date:** 2026-10-18  
**Scope:** provisional `RtspSource` only. Dataset approval was not changed.

## Result

| Check | Result |
| :--- | :--- |
| Mocked unit tests | **31 passed** (`tests/unit/test_cv_rtsp_source.py`, `.venv`, 0.21s) |
| Broader CV unit tests | **96 passed, 1 skipped** in 22.36s (Torch weights not configured; no download) |
| `pytest -c pytest-cv.ini` | **2 skipped** (file-person smoke needs `ILKA_CV_PERSON_WEIGHTS`; RTSP smoke needs `ILKA_RTSP_SMOKE_URL`) |
| Local RTSP smoke | **PASS** — 1 passed, 7.43s, `.venv-cv`, OpenCV 5.0.0 |
| Live reconnect on that publisher | **PASS** — frame `(240, 320, 3)` after the publisher process restarted |
| Physical TP-Link VIGI | **NOT RUN** — host, path, and credentials are not configured |
| Dataset `docs/cv/dataset_approval.html` | **PENDING_REVIEW** (unchanged) |

The smoke publisher was MediaMTX v1.21.2 bound to `127.0.0.1:18554` with loopback-only publish/read, and FFmpeg `testsrc` 320×240. Those pixels are `[MOCK / SYNTHETIC]`. `RtspSource` still sets `is_synthetic=False` because the transport is RTSP. That flag is not a claim of factory footage.

The client set `OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp`. The library does not select transport.

## Code notes

- Open failures keep a safe backend exception as `__cause__`. Causes whose text contains the URL or userinfo are dropped.
- A username that is also a host label no longer rejects the credential-free default `source_id`. A source id that adds a secret still fails.
- NumPy frames are copied before they are returned.

## Not claimed

Production readiness, ONVIF, camera-unavailable events, PPE, fall detection, or a physical camera.
