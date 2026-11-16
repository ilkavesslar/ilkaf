# Datasets

**Status:** register only. `datasets/MANIFEST.yaml` records public benchmarks and the rule for licensed industrial footage. It does not contain images, video, or annotations. Nothing in this directory was downloaded.

Scripts under `scripts/eval/` and `scripts/train/` must not fetch these sets. `downloaded: false` in the manifest is the current fact.

## What a row means

| Field | Values |
| :--- | :--- |
| `id` | Stable name used by a future training config |
| `task` | What the publisher labels support |
| `license_status` | `public_research`, `restricted`, or `unknown` |
| `commercial_use` | `yes`, `no`, or `unclear` |
| `url` | Publisher page. Not a credentialed link |
| `notes` | What was actually read, and the date |
| `ilka_usage` | `allowed_for_eval`, `requires_review`, or `do_not_download_here` |

`allowed_for_eval` is unused. No row has been cleared for ILKA evaluation. `requires_review` means do not train and do not download until a named person updates the row. `do_not_download_here` means the bytes must not enter this repo, CI, or a committed cache.

Check the file without fetching data:

```bash
python scripts/eval/dataset_manifest.py
```

License rules: `docs/datasets/LICENSING.md`.

## Register licensed industrial footage

Industrial video is not added by dropping files into git. Add a manifest row only after a person has the grant in hand and has filled every item below in the change description (the manifest `notes` field records the non-secret summary):

1. Legal basis: contract id or written permission. Do not paste the contract, tokens, camera passwords, or a URL that embeds credentials.
2. Scope: organization, site, camera id, capture window, and whether the grant covers training, evaluation, both, or neither.
3. People: whether workers were informed, the retention limit, and who approves deletion.
4. Storage: a path or bucket outside this git tree. The row stores the ref name, not the objects.
5. `license_status`, `commercial_use`, and `ilka_usage`. A new site capture starts at `requires_review`. It becomes `allowed_for_eval` only in a later reviewed edit that names the grant. It becomes `do_not_download_here` when the grant forbids copying into this repo.
6. Annotator: the publisher's released labels, or a named person who produced the boxes, keypoints, track ids, or fall labels. Record that name outside the image files.

Do not commit raw video, frames, depth, audio, or annotation JSON.

## Never invent annotations

Missing labels stay missing. Do not draw boxes, keypoints, track ids, fall tags, or activity tags to fill a gap, and do not describe synthetic labels as ground truth.

A blank frame used by `scripts/eval/bench_detection_latency.py` is `[MOCK / SYNTHETIC]`. It is a latency probe. It is not a dataset row and its detection count is not a metric.

If a label file is produced later, it has to cite the manifest `id`, the annotator, and the frame range. A script that cannot point at those three writes nothing.
