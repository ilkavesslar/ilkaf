# Human Intelligence live webcam pipeline — fix report

**Branch:** `fix/human-intelligence-live-pipeline`  
**Date:** 2026-11-16  
**Host:** Intel Mac CPU (`.venv-cv`)

## Root causes (why the first webcam test failed)

1. **Wrong script path:** `preview_webcam_person.py` is the legacy detector+tracker+Moving/Waving path. It never called `HumanIntelligenceEngine`, never drew COCO-17 bones, and never showed the eight activity classes.
2. **Pose never executed:** MediaPipe was not installed; `pose_landmarker_lite.task` was missing. HIE therefore used `NullPoseEstimator` (17 unobserved joints).
3. **MediaPipe not viable on this Intel Mac:** `mediapipe==0.10.31` does not exist for this platform; available builds pull `opencv-contrib-python` source builds and/or NumPy 2.x, which conflict with pinned Torch 2.2.2 / NumPy 1.26.4.
4. **Blocking pose killed tracking:** Running Keypoint R-CNN on the UI thread (~3–5 s/frame) starved tracker updates and churned local IDs.

## What was fixed

| Item | Change |
| :--- | :--- |
| Live HIE preview | New `scripts/dev/preview_webcam_hie.py` — boxes, track IDs, skeleton, activity, trails, diagnostics |
| Pose model | TorchVision Keypoint R-CNN ResNet50-FPN (local weights, pinned SHA-256) |
| Weight fetch | `scripts/dev/fetch_pose_keypoint_rcnn.py` |
| Overlay | `cv/intelligence/overlay.py` |
| Backend wiring | `person_preview` prefers Keypoint R-CNN, then MediaPipe, then wrist reader |
| Async pose | Background thread + `_LatestPoseAdapter` so SSDLite/tracking stay continuous |

## Models actually loaded (live)

- Detector: `torchvision-ssdlite320-mobilenet-v3-large@0.17.2`
- Pose: `torchvision-keypointrcnn-resnet50-fpn` (`keypointrcnn_resnet50_fpn_coco-fc266e95.pth`)
- Activity: `ilka-temporal-rules-0.1.0` (PROVISIONAL heuristics)

## Live webcam measurements (honest)

| Metric | Observed |
| :--- | :--- |
| Detection | Working (e.g. ~97–98% on seated subject) |
| Tracking | Stable `t1` after async pose fix |
| Skeleton | Visible COCO-17 bones/joints when pose associates |
| Display FPS | ~7–10 FPS with async pose |
| Detect latency | ~2–3 ms (SSDLite sample) |
| Pose latency | ~5 s/pass on CPU (async, every ~2 s) |
| Activity | Labels appear; **sitting was mis-labeled `person_down` in one run** — provisional rules + partial body framing; **not** tuned away in this fix |

## Remaining limitations

- Keypoint R-CNN is too slow for per-frame pose on Intel Mac CPU; async + cache is required.
- MediaPipe still preferred for speed **if** a compatible wheel can be installed without breaking Torch/NumPy — not achieved here.
- Temporal activity rules remain uncalibrated; false `person_down` / delayed standing–sitting transitions are expected until evaluation on held-out data.
- Falling / person_down acceptance should use safe footage, not unsafe live falls.
- NVIDIA profile unchanged / unverified.

## How to run

```bash
export ILKA_CV_PERSON_WEIGHTS="$(pwd)/data/models/ssdlite320_mobilenet_v3_large_coco.pth"
export ILKA_CV_POSE_WEIGHTS="$(pwd)/data/models/keypointrcnn_resnet50_fpn_coco-fc266e95.pth"
.venv-cv/bin/python scripts/dev/fetch_pose_keypoint_rcnn.py   # once
.venv-cv/bin/python scripts/dev/preview_webcam_hie.py --index 0
```

Press `q` to quit. Window title: `ILKA - Human Intelligence Engine`.
