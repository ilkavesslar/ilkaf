# Local model weights (not committed)

Person-detector weights are downloaded locally and stay out of Git.

Approved fetch (checksum-verified):

```bash
.venv-cv/bin/python scripts/dev/fetch_person_detector_weights.py
```

Expected file after a successful fetch:

```text
data/models/ssdlite320_mobilenet_v3_large_coco.pth
```

Then set `ILKA_CV_PERSON_WEIGHTS` in `.env` to that path. See `cv/detectors/person_cpu.py` for the pinned digest and `docs/development/startup.md` for setup.
