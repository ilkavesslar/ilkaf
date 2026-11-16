# Human Intelligence — Intel Mac and NVIDIA profiles

Status: **PROVISIONAL** device profiles. See ADR 0012.

## Profile A — Intel Mac development

- Interpreter: `.venv-cv` (Python 3.11)
- Torch / TorchVision: `2.2.2` / `0.17.2` (CPU wheels)
- Default detector: SSDLite320 MobileNetV3-Large via `CpuPersonDetector`
- Pose: optional local MediaPipe `.task` under `data/models/`
- No CUDA packages
- Validation: `scripts/dev/check_cv_environment.py`

## Profile B — NVIDIA production

- Separate dependency set (do not install into `.venv-cv` on Intel Mac)
- CUDA-enabled PyTorch matching the host driver
- Optional ONNX / TensorRT export is **PLANNED** and not required for the lab path
- Device selection: `cv.intelligence.device.select_device("nvidia_cuda")`
- Multi-camera workers: `cv.intelligence.workers.CameraFrameWorker`

If NVIDIA hardware is unavailable, mark NVIDIA latency/accuracy results as **unverified**.

## Safety

- One camera worker failure must not stop others.
- Frame queues stay bounded (`maxsize=1` keeps the newest frame).
- Never log RTSP credentials.
