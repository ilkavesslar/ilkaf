# Local model weights (not committed)

Person-detector and pose weights are downloaded locally and stay out of Git (`*.pth`, `*.task`).

## Person detector (SSDLite)

```bash
.venv-cv/bin/python scripts/dev/fetch_person_detector_weights.py
export ILKA_CV_PERSON_WEIGHTS="$(pwd)/data/models/ssdlite320_mobilenet_v3_large_coco.pth"
```

## Pose (Keypoint R-CNN, Intel Mac / CPU)

```bash
.venv-cv/bin/python scripts/dev/fetch_pose_keypoint_rcnn.py
export ILKA_CV_POSE_WEIGHTS="$(pwd)/data/models/keypointrcnn_resnet50_fpn_coco-fc266e95.pth"
```

Optional MediaPipe Pose Landmarker (if `mediapipe` installs on your platform):

```bash
.venv-cv/bin/python scripts/dev/fetch_pose_landmarker.py
```

## Live HIE webcam

```bash
.venv-cv/bin/python scripts/dev/preview_webcam_hie.py --index 0
```
