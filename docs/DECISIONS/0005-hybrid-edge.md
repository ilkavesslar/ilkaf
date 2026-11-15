# ADR 0005: Hybrid / edge inference

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

Latency, privacy, and WAN failure make cloud-only inference a poor default for plants.

## Decision

Architecture must allow inference at edge, site server, central, or hybrid. Integrate via observation/event contracts. Phase 1 still has no inference.

## Consequences

Need buffering/sync design before multi-site WAN. No cloud provider is selected.
