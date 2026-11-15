# Physical TP-Link VIGI camera integration

**Date:** 2026-10-30  
**Branch:** `feature/sprint-3-rtsp-source`  
**Overall:** Both cameras have been opened independently. Each `RtspSource` test decoded 100 real frames. They are not registered, and this is not multi-camera production readiness.

| Stage | Camera 1 `192.168.1.17` | Camera 2 `192.168.1.18` |
| :--- | :--- | :--- |
| IDENTIFIED | VIGI C320I | VIGI C320I |
| AUTHENTICATED | yes, RTSP over TCP | yes, RTSP over TCP |
| RTSP_CONNECTED | yes | yes |
| FRAMES_RECEIVED | 100 real frames | 100 real frames |
| PERSON_DETECTION_VERIFIED | 10 frames, 10 person boxes | 10 frames, 0 person boxes |
| Camera registry | **NOT REGISTERED** | **NOT REGISTERED** |

## A. Executive summary

Both devices are TP-Link VIGI C320I cameras. Each was opened separately over RTSP TCP with the existing `RtspSource`, and each test decoded 100 real 1920×1080 frames. The same account variables were used for both. Camera 1’s stored host was not changed. No camera, switch, or router setting was changed.

## B. Network discovery

Laptop: `192.168.1.14/24` on Wi-Fi. Gateway: `192.168.1.1` (ZTE F670LV9.0 from the earlier HTTP title).

| Role | Address now | MAC now | Evidence |
| :--- | :--- | :--- | :--- |
| IPC, router list said `.12` | `192.168.1.18` | `BC-07-1D-67-69-07` | Ping TTL 64. OUI `BC-07-1D` is TP-Link Systems Inc. |
| IPC, router list said `.13` | `192.168.1.17` | `BC-07-1D-67-6A-C0` | Ping TTL 64. Same OUI. |
| ES210GP MAC from the operator | `192.168.1.16` | `A8-29-48-FD-58-2A` | Reachable. HTTP 80 is a TP-Link login page. |
| Address the operator called the switch | `192.168.1.11` | `16-38-31-11-48-76` | Answers ping. This MAC is locally administered and is not the ES210GP MAC. Ports 80, 443, 554, 8043, and 8088 are closed. |

`192.168.1.12` did not answer ping or the checked TCP ports, and ARP has no MAC for it. `192.168.1.13` did not answer ping or those ports. Its ARP entry is a different locally administered MAC, not `BC-07-1D-67-6A-C0`.

Checked on both cameras: TCP 80, 443, 554, and 2020 open. TCP 8000 and 8080 closed.

One ONVIF WS-Discovery probe (`239.255.255.250:3702`) returned `NetworkVideoTransmitter` replies from `.17` and `.18` only. `192.168.1.8` returned a non-ONVIF SOAP fault. No other camera replied.

Omada Controller ports 8043 and 8088 are closed on `.11` and `.16`. There is no authorized Omada session on this laptop. Switch port, PoE, VLAN, and traffic counters were **not** read. No switch setting was changed.

## C. Camera identification

Both ONVIF scopes say:

- `onvif://www.onvif.org/name/VIGI-C320I`
- `onvif://www.onvif.org/hardware/VIGI-C320I`
- Profiles: Streaming and T
- Device service: `http://<ip>:2020/onvif/device_service`

Firmware was not read. That requires an authenticated ONVIF or web session.

| Camera | Current IP | MAC | Model |
| :--- | :--- | :--- | :--- |
| Router IPC 1 | `192.168.1.18` | `BC-07-1D-67-69-07` | VIGI C320I |
| Router IPC 2 | `192.168.1.17` | `BC-07-1D-67-6A-C0` | VIGI C320I |

## D. RTSP configuration

Official VIGI RTSP paths, from TP-Link FAQ 3718 and FAQ 4201, which list C320I:

- Main stream: `rtsp://<ip>:554/stream1`
- Sub stream: `rtsp://<ip>:554/stream2`
- Default RTSP port: 554
- Account: the camera account created in the VIGI app, not a guessed default

Unauthenticated `ffprobe -rtsp_transport tcp` against `rtsp://192.168.1.17:554/stream1` and `rtsp://192.168.1.18:554/stream1` both returned `401 Unauthorized`. Codec, resolution, and frame rate were not retrieved.

No password is stored. These variables are absent: `ILKA_CAMERA_HOST`, `ILKA_CAMERA_RTSP_PORT`, `ILKA_CAMERA_USERNAME`, `ILKA_CAMERA_PASSWORD`, `ILKA_CAMERA_STREAM_PATH`. The camera registry has no stream URL or password column. Nothing was written into git.

## E. ILKA changes

No application code was changed in this pass. `RtspSource` remains `cv/streams/rtsp.py`. This file is the updated discovery report.

## F. Validation labels

| Check | `.17` | `.18` |
| :--- | :--- | :--- |
| DISCOVERED | yes | yes |
| IDENTIFIED | VIGI C320I | VIGI C320I |
| AUTHENTICATED | no | no |
| RTSP_CONNECTED | no | no |
| STREAM_VERIFIED | no | no |
| FRAMES_RECEIVED | 0 | 0 |
| PERSON_DETECTION_VERIFIED | not tested | not tested |

## G. Test results

Physical `ffprobe` without credentials: both cameras, exit failure, `401 Unauthorized`. No frames decoded.

The earlier focused CV unit run on this branch remains **96 passed, 1 skipped**. It was not repeated in this pass. It does not open these cameras. `ILKA_CV_PERSON_WEIGHTS` is still unset, so live person detection stays skipped.

## Camera 1 frame validation

An earlier unauthenticated and first authenticated attempt returned 401. A later single TCP attempt, using the Windows user account variables already in the process, succeeded. Credentials were not printed. No camera, router, switch, or VLAN setting was changed.

OpenCV reported H.264, 1920×1080, 25 FPS. `RtspSource` then read 100 consecutive frames on 2026-10-30:

| Item | Result |
| :--- | :--- |
| Source id | `vigi-c320i-192.168.1.17` |
| `source_kind` | `rtsp` |
| `is_synthetic` | false |
| Mock label | empty |
| Frames | 100 |
| Read failures | 0 |
| Reconnects | 0 (failure path not exercised) |
| Shape | `(1080, 1920, 3)`, `uint8` |
| Indexes | 0 through 99, contiguous |
| Timestamps | `2026-10-30T12:44:14.095355+00:00` to `2026-10-30T12:44:17.045471+00:00` |
| Read rate | 33.6 frames/s over 4.25 s |
| Close | called twice |

The 25 FPS value is the stream metadata. The 33.6 figure is how fast ILKA pulled already buffered frames, not a claim that the camera encodes at 33.6 FPS. No images were saved. The registry still has no password column, so this camera was not inserted.

## Camera 2 frame validation

Port 554 on `192.168.1.18` was open. One TCP attempt with the same account variables used for Camera 1 succeeded. `ILKA_CAMERA_HOST` was left at `192.168.1.17`. Credentials were not printed.

OpenCV reported H.264, 1920×1080, metadata 25 FPS. `RtspSource` then read 100 consecutive frames on 2026-10-30:

| Item | Result |
| :--- | :--- |
| Source id | `vigi-c320i-192.168.1.18` |
| `source_kind` | `rtsp` |
| `is_synthetic` | false |
| Mock label | empty |
| Frames | 100 |
| Read failures | 0 |
| Indexes | 0 through 99, contiguous |
| Timestamps | `2026-10-30T12:49:56.091638+00:00` to `2026-10-30T12:49:59.069949+00:00` |
| Wall time | 4.27 s |
| Close | called twice |

The metadata frame rate is 25 FPS. The wall time is not reported as the camera frame rate. No images were saved. Reconnect after a dropped stream was not provoked.

Ten later live frames were passed to the existing CPU person detector and the local weights file. Result: 0 person boxes, 0 invalid observations. Model: `torchvision-ssdlite320-mobilenet-v3-large`, version `0.20.1+cpu`. That is an observation result for those frames, not an incident result and not proof the camera cannot see a person.

## Person detection on Camera 1

`ILKA_CV_PERSON_WEIGHTS` is unset. The existing local weights file was passed explicitly and its integrity check passed. Ten further live frames, not the same 100-frame sample, produced 10 valid person boxes. Confidence was 0.2529 to 0.2661. Model: `torchvision-ssdlite320-mobilenet-v3-large`, version `0.20.1+cpu`. These are observations, not incidents. PPE and fall detection were not run.

## Focused unit tests

Not re-run in this pass. The previous run on this branch was **96 passed, 1 skipped**. The skip is the live CPU detector test because `ILKA_CV_PERSON_WEIGHTS` is unset.

## Live dashboard preview

The camera registry still has no secret column, so the live view is a development-only API, not a registry record.

`GET /api/v1/lab/cameras` and `GET /api/v1/lab/cameras/{camera_id}/mjpeg` require the existing bearer token and `cameras:read`. `ENVIRONMENT=production` or `ILKA_LAB_CAMERAS_ENABLED` unset returns 404. When `ILKA_LAB_CAMERA_ORGANIZATION_ID` and `ILKA_LAB_CAMERA_SITE_ID` are set, the existing site check applies. Responses contain the camera id, display name, host, source id, and health. They do not contain an RTSP URL or password.

Each camera id has one `RtspSource` reader. The reader keeps only the latest JPEG. The browser fetches MJPEG with the Auth0 bearer token and stops the request when the dashboard unmounts. React shows loading, live, disconnected, and unauthorized states from that request. It does not mark a card connected unless frames are arriving.

A local hub smoke test opened both readers together. Each became `live` at 1920×1080, with different JPEG sizes (134050 and 160204 bytes). That was not a browser session.

```powershell
$env:ILKA_LAB_CAMERAS_ENABLED = "true"
cd backend
uvicorn app.main:app --reload
```

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173/` and sign in. The live section is on the dashboard.

Automated tests in this pass:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_lab_camera_streams.py tests/unit/test_lab_cameras_api.py -q --tb=short -p no:cacheprovider
```

**8 passed** in 1.79s.

```powershell
cd frontend
npm test
npm run build
```

**26 passed**. Production build succeeded.

## H. Outstanding

1. Set the VIGI account locally, without pasting it into chat. For the first camera, the environment needs `ILKA_CAMERA_USERNAME`, `ILKA_CAMERA_PASSWORD`, and optionally `ILKA_CAMERA_HOST` (`192.168.1.17` or `192.168.1.18`), `ILKA_CAMERA_RTSP_PORT` (`554`), and `ILKA_CAMERA_STREAM_PATH` (`/stream1`). Say when those variables are set.
2. An authorized Omada Controller session is required to map each MAC to an ES210GP port. The controller is not reachable on the switch addresses checked here. The switch MAC currently answers at `192.168.1.16`, not `192.168.1.11`.
3. Do not change camera IPs. The router list is stale relative to ARP: the IPC MACs have moved from `.12`/`.13` to `.18`/`.17`.
