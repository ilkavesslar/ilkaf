# Human-intelligence data, training, and eval

- Objective: register public human datasets and lab model cards, and add a CPU latency harness plus detection-score helpers that refuse to invent numbers.
- Files inspected: `cv/detectors/person_cpu.py`, `scripts/dev/bench_cpu_person_detector.py`, `docs/AI_MODELS.md`, `ai/README.md`, and the untracked lab detector registry under `cv/detectors/` (read only).
- Files changed: `datasets/MANIFEST.yaml`, `datasets/README.md`, `docs/datasets/LICENSING.md`, `ai/registry/models.py`, `ai/registry/registry.yaml`, `ai/registry/__init__.py`, `scripts/eval/bench_detection_latency.py`, `scripts/eval/metrics.py`, `scripts/eval/dataset_manifest.py`, `scripts/eval/test_metrics.py`, `scripts/eval/test_registry.py`, `scripts/train/README.md`, `scripts/train/config_example.yaml`, `docs/models/HUMAN_INTELLIGENCE_MODELS.md`, this report.
- Decisions: SSDLite stays the Intel Mac default because the pinned CPU adapter already exists. YOLO, RT-DETR, MediaPipe, and RTMPose are placeholders with `not_bundled` weights. No manifest row is `allowed_for_eval`. `commercial_use: yes` is unused. OKS and IDF1 return `value=None`.
- Tests: from `scripts/eval/`, `.venv/bin/python -m unittest test_metrics.py test_registry.py` — 13 passed. `python ai/registry/models.py` and `python scripts/eval/dataset_manifest.py` exit 0. On `.venv` (no PyTorch) `bench_detection_latency.py` exits 0 with `latency: not_measured`. On `.venv-cv`, with the existing local SSDLite file, one CPU run on a 320×320 `[MOCK / SYNTHETIC]` blank frame (1 warmup, 8 timed) printed `model_version=0.17.2`, `p50_ms=100.059`, `p95_ms=142.104`, and `warmup_observation_count=0`. That count is not precision or recall. Those timings are this machine only, not a service level.
- Unresolved issues: PoseTrack, CrowdPose, UR Fall, and UP-Fall still have no confirmed data deed. COCO image licenses stay per-file. No bake-off has been run. No trainer exists.
- Risks: a later edit could set `allowed_for_eval` without a grant. The manifest checker blocks that pairing only when `commercial_use` is `no`. Reviewers still have to reject a casual flip of COCO or the unknown rows.
- Recommended next action: counsel confirms or corrects the four unknown rows before any download. A bake-off, if it happens, uses the same frames as SSDLite and writes measured latency only.

## Not downloaded

COCO 2017 detection, COCO 2017 keypoints, CrowdHuman, CrowdPose, MOT17, MOT20, PoseTrack, NTU RGB+D 120, UR Fall, UP-Fall. SSDLite, YOLO, RT-DETR, MediaPipe, and RTMPose weights were not fetched by this change.
