# Sprint 3 M5 — quality / validation

**Agent:** Builder  
**Branch:** `feature/sprint-3-m3-cpu-detector`  
**Date:** 2026-10-14

## Status

Lab validation only. Not production readiness, accuracy certification, RTSP/ONVIF ingestion, PPE detection, or incident detection. No backend CV API.

## Latest verified results

- Backend unit tests: **125 passed**, **1 skipped**, **2 warnings**.
- CV unit suite (`.venv-cv`): **62 passed**, **1 warning**. That warning is `asyncio_mode` unknown in `.venv-cv`.
- Live `FileSource` → `CpuPersonDetector` smoke test: **1 passed** in **29.50s**. `ILKA_CV_PERSON_WEIGHTS` explicitly pointed at the existing local weights file. The isolated smoke test skips when its optional CPU dependencies or that explicit weights file are missing.
- Separate preview CLI check: **30** frames processed, **7** person observations, CPU inference, no output video written.
- FileSource frames and CV observations remain marked **`[MOCK / SYNTHETIC]`**.

## M4 preview

`scripts/dev/preview_person_detection.py` is the provisional lab CLI (`FileSource` → `CpuPersonDetector` → `Observation`). The verified check above did not write an output video.

## Historical sample (not reproduced)

An older note for `data/videos/people-detection (1).mp4` cited **596** frames and **300** person observations. That sample review was **not** reproduced in the 2026-10-14 run. It is not the 30-frame preview result and not an accuracy metric.

## Tests added in M5

- `tests/unit/test_preview_person_detection.py` — missing video / missing weights → non-zero exit (no Torch load)
- `tests/unit/test_cv_file_source.py` — default `source_id` is the filename
- `tests/unit/test_cv_detector_mapping.py` — exact normalized box for a known pixel box

The isolated smoke test skips if its optional CPU dependencies or explicit weights file are missing.
