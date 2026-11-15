# Camera architecture

**Status:** Production cameras are **PLANNED** (**PoE IP**, not laptop webcams). Camera **metadata** registry APIs are **IMPLEMENTED**. Lab ingest is `FileSource` (local files, `[MOCK / SYNTHETIC]`). Webcam use is **dev-only** and must be labeled `[MOCK / SYNTHETIC]`.

Canonical for this topic. Older `CAMERA_ARCHITECTURE.md` points here.

## Physical layers (future deployment)

1. **Camera:** PoE IP cameras (ONVIF Profile S where the vendor supports it).
2. **Network:** Managed PoE switch (VLAN/segmentation **PLANNED**).
3. **Edge:** Site workstation/server for ingest and optional GPU inference.
4. **Application:** ILKA backend (modular monolith initially).
5. **Data:** PostgreSQL (Neon in hosted/dev).
6. **Operator:** Web dashboard.

Vendor SKUs are **NOT DECIDED**. Do not hard-code a camera brand in `backend/` or `frontend/`.

## Vendor abstraction

`cv/` should expose a **camera adapter** interface, for example:

- identity, site/zone placement
- stream access (RTSP URL from a secret store, not git)
- optional ONVIF: discovery, reboot, some config
- health: reachable, streaming, last frame UTC, error class
- permissions (who may view/export)
- recording/retention **policy references** (implementation later)
- calibration / zone overlay references

Replacing a vendor means a new adapter, not a rewrite of rules, incidents, or UI.

## Ingest principles

- Bounded buffers; drop frames rather than unbounded RAM.
- Reconnect with backoff; after a threshold emit **camera unavailable** (observable).
- Timestamps: prefer camera/NTP; record clock-skew when present.
- Multi-camera: isolate failures per camera.
- Browser viewing protocol (WebRTC vs LL-HLS vs other): **NOT DECIDED** (P8).

## What exists vs what not to build now

**Implemented:** camera **metadata** registry (site-scoped APIs; no RTSP URLs or credentials on the row). Sprint 3 lab CV ingest is **`FileSource`** (local video, `[MOCK / SYNTHETIC]`) and a provisional **`RtspSource`** (timeouts, credential-safe ids, bounded reconnect). A localhost `[MOCK / SYNTHETIC]` publisher smoke test has been run. A physical camera has not. Neither ingest path is a factory adapter or a production integration.

**Not implemented (production ingest remains later / Phase 3):** no ONVIF, no reconnect/backoff **camera unavailable** event, no recording, no live grid, no detection-to-incident path.

## Fail-safe

A silent missing stream is a defect. Persistent dropout → monitoring degraded / camera unavailable, never implied “no incidents.”
