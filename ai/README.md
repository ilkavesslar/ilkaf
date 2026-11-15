# AI & Machine Learning Subsystem

**Status:** **SCAFFOLDED**. Sprint 1 does not install or run models in `ai/`. Frame-level lab detection lives in `cv/` (optional isolated `.venv-cv`), not here.

This layer will later contain:

- object detection
- PPE detection
- tracking
- zone analysis
- proximity analysis
- model inference

Do not add PyTorch, CUDA, YOLO, or OpenCV to the **backend** environment or to `ai/` until a later sprint explicitly requires them. OpenCV (and CPU Torch) may be installed only in the isolated lab CV venv used by `cv/` (`cv/README.md`).

## Directory Layout (Planned)

```text
ai/
├── models/                 # Model registry metadata and weights references
├── pipelines/              # Inference and preprocessing pipelines
└── evaluation/             # Model benchmark scripts, confusion matrices, explainability metrics
```
