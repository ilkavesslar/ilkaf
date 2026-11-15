# Computer Vision Subsystem Architecture (docs/computer-vision)

**Status:** **PLANNED / TARGET ARCHITECTURE**. This page describes the intended production CV system. It is **not** a description of current code.

**Currently implemented (lab):** see [`cv/README.md`](../../cv/README.md) — FileSource, provisional RtspSource, Observation, provisional CPU person detector, lab CLI. The detector loads only an explicit local weights file that matches the pinned SHA-256 and does not download weights. File frames and observations stay `[MOCK / SYNTHETIC]`. RTSP frames are non-synthetic and are not an incident pipeline. A localhost `[MOCK / SYNTHETIC]` publisher smoke test has been run; a physical camera has not. Independent QA/security review and human closure remain pending. Production readiness and accuracy certification remain open. **Not implemented:** production RTSP/ONVIF integration, PPE detectors, tracking, zone-breach products, or dashboard alerts.

## 1. Role of Computer Vision in ILKA (target)

The production Computer Vision (CV) subsystem is intended to handle real-time edge processing of live industrial camera video feeds:

- **RTSP / ONVIF Ingestion**: Decoding high-bandwidth video streams with low latency.
- **Frame Queue Management**: Bounded ring buffers and adaptive frame dropping to prevent memory bloat and CPU starvation.
- **Object Detection & Spatial Tracking**: Real-time localization of workers, PPE items, machinery, and vehicles (forklifts, AGVs).
- **Geometric Zone Monitoring**: Ray-casting / point-in-polygon algorithms determining whether worker bounding boxes breach designated exclusion zones.

---

## 2. Core Mandate: Probabilistic Vision & Metadata Requirements

> [!IMPORTANT]
> **Probabilistic Principle**: CV detections are **probabilistic observations**. Environmental factors (lighting, occlusions, lens dust, viewing angle) directly affect detection accuracy.

Every vision detection emitted from the CV edge worker must include the following metadata envelope:

```json
{
  "timestamp": "2026-08-19T14:45:10.123Z",
  "camera_id": "cam-assembly-line-04",
  "zone_id": "zone-robotics-perimeter",
  "detection_type": "RESTRICTED_ZONE_BREACH",
  "confidence": 0.884,
  "model_name": "ilka-yolo-ppe-detector",
  "model_version": "v1.2.0-fp16",
  "bounding_box": {
    "x_min": 0.342,
    "y_min": 0.512,
    "x_max": 0.485,
    "y_max": 0.891
  },
  "polygon_coordinates": [
    {"x": 0.342, "y": 0.891},
    {"x": 0.485, "y": 0.891}
  ],
  "track_id": "trk_8921"
}
```

---

## 3. Fail-Safe Stream Resilience

1. **Stream Health Monitoring**: Every active RTSP stream is monitored via heartbeat pings and frame arrival intervals.
2. **Graceful Reconnection**: On disconnection, the stream worker initiates an exponential backoff reconnection loop.
3. **Blind-Spot Alerting**: If a stream remains disconnected beyond a threshold (e.g., 5 seconds), a `CAMERA_STREAM_DROPOUT` safety alert is immediately broadcast to the operator dashboard.
4. **Human Verification Standard**: High-consequence detections flagged by the vision pipeline require human operator verification before triggering plant escalations.
