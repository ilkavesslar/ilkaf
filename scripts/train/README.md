# Training

**Status:** outline only. This directory does not train a model. Running the commands below is not possible yet, because there is no trainer entrypoint. Nothing here has produced a checkpoint.

`config_example.yaml` is a template. `claim_training_completed` is `false`. `output_checkpoint` is null. Both download flags are `false`.

## What a real run has to record before anyone says it finished

Do not write "training completed", "fine-tune done", or an accuracy figure unless every item below exists as files from that run:

1. Git commit of the code that ran.
2. `datasets/MANIFEST.yaml` id, and a human note that `ilka_usage` allows the run. Today no row is `allowed_for_eval`. `do_not_download_here` rows are not training data.
3. Annotation source: publisher labels or a named annotator. No invented boxes, keypoints, track ids, or fall tags.
4. The filled config (a copy of the template with the blanks replaced) and its hash.
5. Init weights: `model.init_model_id` must be a registry id. For `ssdlite320-mobilenet-v3`, the local file must match the pin in `cv/detectors/person_cpu.py`. The trainer must not download it.
6. Device profile actually used (`intel_mac_cpu` or `nvidia_cuda`), seed, and the log of the process exit code.
7. A checkpoint path outside git, plus its SHA-256, written only after the process exits 0.
8. Eval counts passed through `scripts/eval/metrics.py`. OKS and IDF1 stay uncomputed until those stubs are replaced. Do not fill them with a published paper score.

A registry card may use `provenance: finetuned` only together with `training_run_record` pointing at that bundle. `ai/registry/models.py` rejects a fine-tuned card without it.

## Order of work when a trainer exists later

1. `python scripts/eval/dataset_manifest.py` exits 0 and the chosen id is not `do_not_download_here`.
2. `python ai/registry/models.py` shows the init model. The default stays `ssdlite320-mobilenet-v3` until a bake-off says otherwise (`docs/models/HUMAN_INTELLIGENCE_MODELS.md`).
3. Copy `config_example.yaml` to a run directory outside git. Set `dataset.manifest_id`, `dataset.split`, and `model.init_model_id`. Leave `claim_training_completed` false until step 7.
4. Train on the backend or a lab machine. Do not train inside an HTTP request. Do not point the job at a camera password or a `.env` value.
5. On failure, keep the log, write no checkpoint, and leave the claim flag false.
6. On success, hash the checkpoint, run eval, and store precision, recall, and F1 only as the outputs of `precision_recall_f1` on counted errors. Undefined precision or recall stays null. It is not replaced with 0 or 1.
7. A person sets `claim_training_completed` true in the run record, not in this example file, and opens a registry change that adds `training_run_record`.

## Refusal

This directory refuses to claim that training completed. There is no checkpoint to hash. There is no loss curve. There is no fine-tuned model id. Copying `config_example.yaml` into a card does not create one.
