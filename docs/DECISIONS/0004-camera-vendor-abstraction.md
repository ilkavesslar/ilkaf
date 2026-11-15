# ADR 0004: Camera vendor abstraction (PoE IP)

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

Production will use PoE IP cameras and RTSP; ONVIF where supported. Laptop webcams are not the production architecture.

## Decision

Isolate vendors behind `cv/` adapters (identity, stream secret ref, health, optional ONVIF). Webcams are `[MOCK / SYNTHETIC]` for development only.

## Consequences

Brand changes do not rewrite backend rules or UI. Browser playback protocol remains **NOT DECIDED**.
