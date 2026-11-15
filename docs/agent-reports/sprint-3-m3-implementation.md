# Sprint 3 M3 — optional CPU person detector

**Agent:** Builder  
**Branch:** `feature/sprint-3-m3-cpu-detector`  
**Date:** 2026-09-20

## Status

PROVISIONAL lab adapter: TorchVision SSDLite320 MobileNetV3-Large, CPU only. Not an ADR for production models (N6 still open). Observations are not incidents.

## Weights

`ILKA_CV_PERSON_WEIGHTS` if set. Fetch script uses TorchVision DEFAULT URL at runtime. Checksum verification is not implemented.
