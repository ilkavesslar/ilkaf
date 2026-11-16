# Human Intelligence Engine — performance & evaluation report

**Date:** 2026-11-16  
**Host:** Intel Mac (CPU), `.venv-cv`  
**Status:** Measured lab results only. No production accuracy claim.

## What was measured

| Scenario | Result |
| :--- | :--- |
| Synthetic two-person track association (pre-supplied boxes, no pose) | 2 distinct local IDs (`bench-cam:t1`, `bench-cam:t2`) |
| HIE `process_frame` mean latency (20 frames, 640×480 synthetic) | **3.27 ms** |
| HIE `process_frame` p95 latency | **3.92 ms** |
| Implied throughput for that path only | ~306 FPS (tracking+activity only; **excludes** detector and pose) |
| Activity on short synthetic motion | `unknown` (correct: insufficient temporal evidence) |
| Keypoints without pose estimator | 17× visibility 0 (not invented) |

## What was not measured (do not invent)

- Detector mAP50 / mAP50-95 on held-out industrial footage
- Tracker HOTA / IDF1 / ID switches on MOT
- Pose OKS mAP / PCK
- Activity per-class precision/recall / confusion matrix on fall datasets
- Re-ID Rank-1 / mAP
- End-to-end RTSP multi-camera FPS with SSDLite + pose
- NVIDIA CUDA / TensorRT latency (**hardware unavailable / unverified**)

Proposed targets in product discussions are **not** measured results.

## Automated tests (this branch)

- CV HIE unit suite + mapping: **230 passed, 5 skipped** (`tests/unit/test_cv_*.py`, `backend/tests/test_detection_intelligence_mapping.py`)
- Frontend: **37 passed** (vitest)
- Frontend production build: **ok**

## Limitations

1. Default detector remains SSDLite320 MobileNetV3-Large until a reproducible bake-off on licensed footage selects an alternative.
2. YOLO / RT-DETR / ByteTrack / BoT-SORT are optional or scaffolded adapters; they are not auto-selected.
3. Pose uses MediaPipe→COCO-17 when available; missing joints stay unobserved.
4. Activity recognizer is temporal rule-based (PROVISIONAL thresholds). ST-GCN / PoseC3D are training hooks only until licensed data exists.
5. Cross-camera identity is probabilistic and anonymous; no facial recognition.
6. Datasets are catalogued with licenses; weights and restricted downloads are not committed.
