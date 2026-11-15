# Agent report: Intel Mac CV environment repair

Status: lab CV environment repaired on Intel macOS without changing backend/frontend/Neon.

## Summary

- Recreated isolated `.venv-cv` with pip-only matching CPU wheels (`torch==2.2.2`, `torchvision==0.17.2`).
- Root cause of `torchvision::nms`: conda TorchVision `_C.so` failed `dlopen` (libc++ ABI mismatch); ops never registered.
- Fetched pinned SSDLite weights via `scripts/dev/fetch_person_detector_weights.py` (gitignored).
- Added Intel Mac pin file, setup doc, and `scripts/dev/check_cv_environment.py`.

## Verification (executed)

- `pytest -c pytest-cv.ini`: 1 passed, 1 skipped (RTSP opt-in)
- Backend unit CV tests via `.venv`: 24 passed, 4 skipped
- `/ready` remained `database=ok`; frontend `:5173` HTTP 200
