# AI models

**Status:** `ai/` remains **SCAFFOLDED**. Lab `cv/` has a **PROVISIONAL** SSDLite320 MobileNetV3-Large CPU adapter. Weights are an explicit local `.pth` (not committed) and must match the pinned SHA-256. Detector construction does not download weights. This is not a production model registry. Production model ADR / selection remains **deferred**. Frameworks **PROVISIONAL**.

## Planned split

- `cv/`: frame-level detection/tracking (PPE, person, zone geometry)
- `ai/`: temporal aggregation, anomaly/risk scoring, explainability

Provisional CV stack: OpenCV + PyTorch / YOLO wrappers. **DECISION REQUIRED** for edge acceleration (TensorRT/ONNX vs PyTorch).

## Non-negotiable metadata

Confidence, model name/version, camera/zone IDs, UTC timestamp, bounding box/polygon. See `docs/ai/README.md`.

Predictions are candidate observations. Safety-critical or punitive outcomes require HITL verification.

Lab isolated smoke lives in `tests/cv_ai/` (`pytest-cv.ini`). Production evaluation under `ai/evaluation/` is **not** implemented.
