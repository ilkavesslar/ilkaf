# Camera infrastructure

**Status:** **SCAFFOLDED**. Sprint 1 does not stream video or talk to cameras.

Future camera infrastructure will handle:

- camera registration
- RTSP / video sources
- stream health
- frame acquisition
- camera configuration
- camera status

Production cameras are expected to be PoE IP cameras. Vendor adapters and secret handling belong in later sprints. See `cv/` for the planned computer-vision module layout and `docs/CAMERA-ARCHITECTURE.md` for architecture.
