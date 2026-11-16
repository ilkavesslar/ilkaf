# Human-intelligence models

**Status:** **PROVISIONAL**. This is not a production model ADR. Production selection remains **NOT DECIDED**. No accuracy number is stated in this document because none was measured here.

Cards live in `ai/registry/registry.yaml` and are checked by `ai/registry/models.py`.

## Default: SSDLite320 MobileNetV3-Large on Intel Mac CPU

`ssdlite320-mobilenet-v3` is the default because it is the one detector this repo already runs and checks:

- The lab adapter is `CpuPersonDetector` (`cv/detectors/person_cpu.py`).
- Inference is forced onto CPU. `nvidia_cuda` is not a profile for this card.
- Weights are a local `.pth`. The constructor refuses a file whose SHA-256 does not match the pin in that module, and it does not download.
- The approved fetch, when a person chooses to run it, is `scripts/dev/fetch_person_detector_weights.py`. The weights file is not in git.
- `scripts/eval/bench_detection_latency.py` times that adapter on a blank `[MOCK / SYNTHETIC]` frame only when PyTorch, TorchVision, NumPy, and the local file are already present. If they are not, the script exits 0 and prints `latency: not_measured`. A skip is not a latency of 0 ms.

"Verified" here means the load path, the checksum pin, and the CPU device are real. It does not mean a detection rate, a precision, a recall, or a fit for a plant floor.

## YOLO and RT-DETR stay unselected

`ultralytics-yolo` and `rtdetr-placeholder` are names in the registry. They are `placeholder`, `measured: false`, and `weights_policy: not_bundled`.

They are not the default, including when they are more often cited than SSDLite. A replacement has to beat the pinned SSDLite on a bake-off that records all of the following, from a run that actually happened:

- The same frames, the same threshold, and the same machine profile (`intel_mac_cpu` or `nvidia_cuda`).
- Latency from `scripts/eval/bench_detection_latency.py` or a successor that refuses to invent a sample.
- Precision, recall, and F1 from counts produced by `scripts/eval/metrics.py` against publisher or human labels. OKS and IDF1 stay uncomputed until those functions are implemented.
- A weights pin. A bare Ultralytics model name is not acceptable, because that API downloads weights.
- A dataset row in `datasets/MANIFEST.yaml` whose `ilka_usage` allows that eval. Today none do.

Until that record exists, the Intel Mac lab path stays on SSDLite.

## Pose

`mediapipe-pose-placeholder` and `rtmpose-placeholder` reserve ids for a future COCO-17 estimator. No package, checkpoint, or OKS result is registered. `oks_stub` returns `computed=false` and `value=None`.

## Provenance

Every current card is `pretrained`. `finetuned` is rejected unless a card carries a `training_run_record`. This tree has no such record. `scripts/train/` does not write checkpoints and does not claim that training ran.

## Device profiles

| model_id | intel_mac_cpu | nvidia_cuda |
| :--- | :--- | :--- |
| `ssdlite320-mobilenet-v3` | lab path exists | not a profile |
| `ultralytics-yolo` | candidate, not measured | candidate, not measured |
| `rtdetr-placeholder` | candidate, not measured | candidate, not measured |
| `mediapipe-pose-placeholder` | candidate, not measured | not a profile |
| `rtmpose-placeholder` | candidate, not measured | candidate, not measured |
