# Licensing

**Status:** compliance rules for `datasets/MANIFEST.yaml`. This page is not legal advice and is not itself a license. Notes in the manifest were checked against public publisher pages on 2026-11-16.

No dataset in the manifest is cleared for ILKA. `ilka_usage: allowed_for_eval` is defined and unused. `commercial_use: yes` does not appear.

## Rules

1. A script in this repo must not download a manifest dataset. `downloaded: false` stays false until a human changes it in a reviewed edit after the bytes are stored outside git under a recorded grant.
2. `do_not_download_here` forbids fetching, mirroring, CI caching, and committing the bytes. CrowdHuman, MOT17, MOT20, and NTU RGB+D 120 are in this class.
3. `requires_review` forbids training and forbids an eval download until a named person updates the row. COCO, CrowdPose, PoseTrack, UR Fall, and UP-Fall are in this class.
4. `commercial_use: no` cannot be paired with `allowed_for_eval`. The manifest checker rejects that pair.
5. `commercial_use: unclear` or `license_status: unknown` is not a grant. Absence of a published prohibition is not permission.
6. Image rights and annotation rights are separate. COCO annotations are CC BY 4.0 (attribution required). COCO images stay under their Flickr licenses. Using the annotation JSON does not clear the images.
7. A non-commercial or no-redistribution dataset license follows a model trained on that data. Do not commit those weights, and do not treat a derived checkpoint as an ILKA-owned file.
8. Setting `allowed_for_eval` requires a reviewed manifest edit that names the deed, the split, and the storage location outside git. The edit still must not commit the bytes.
9. Industrial footage needs a written grant before a row is added. Record the contract id in the change description. Do not put the contract, camera passwords, or credentialed URLs in the manifest or in logs.
10. Worker video is limited to the purpose, site, and retention in the grant. A camera configuration change is not a new license.
11. Annotations come from the publisher's released labels or from a named person. Missing labels stay missing. Do not generate boxes, keypoints, track ids, or fall tags and store them as ground truth.
12. Synthetic probes are labeled `[MOCK / SYNTHETIC]`. They are not manifest entries and their detector outputs are not metrics.
13. Re-check the publisher page before any future download. A catalog tag (Hugging Face, a paper PDF, or a third-party README) does not override the publisher page. Where this manifest says the deed was not confirmed, leave the row at `unknown` / `unclear`.

## Summary of the current rows

| id | license_status | commercial_use | ilka_usage | Why |
| :--- | :--- | :--- | :--- | :--- |
| `coco-2017-detection` | public_research | unclear | requires_review | Annotations CC BY 4.0; images are Flickr and often non-commercial |
| `coco-2017-keypoints` | public_research | unclear | requires_review | Same split of rights as COCO detection |
| `crowdhuman` | restricted | no | do_not_download_here | Non-commercial research and education; no redistribution |
| `crowdpose` | unknown | unclear | requires_review | No dataset license in the official repository |
| `mot17` | restricted | no | do_not_download_here | CC BY-NC-SA 3.0 |
| `mot20` | restricted | no | do_not_download_here | CC BY-NC-SA 3.0 |
| `posetrack` | unknown | unclear | requires_review | Publisher deed not confirmed in this pass |
| `ntu-rgbd-120` | restricted | no | do_not_download_here | ROSE Lab agreement; request-gated; no redistribution or commercial use |
| `ur-fall` | unknown | unclear | requires_review | Official page cites the paper and states no data license |
| `up-fall` | unknown | unclear | requires_review | Citation requested; article CC BY 4.0 was not verified as the file license |

## What this repo will not do

- It will not vendor COCO, CrowdHuman, CrowdPose, MOT, PoseTrack, NTU RGB+D 120, UR Fall, or UP-Fall.
- It will not copy SSDLite, YOLO, RT-DETR, MediaPipe, or RTMPose weights into git as part of dataset registration.
- It will not publish an accuracy number for any of these sets. No evaluation against them has been run.
