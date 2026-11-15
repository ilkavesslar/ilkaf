# Deployment architecture

**Status:** **PLANNED**. No Docker/k8s **IMPLEMENTED**. Docker **PROVISIONAL**.

Canonical for this topic.

## Environments

```text
Dev workstation → Neon development project → branches → migrations → tests
        → staging (later) → production (human-only)
```

Phase 1: run API + UI locally against Neon **dev**. No production Neon from agents.

## Hybrid topology (later)

- **On-prem / edge:** cameras, switch, optional GPU box, optional local API replica.
- **Central:** Postgres, operator UI, aggregation, model registry.
- **Cloud:** optional; provider **NOT DECIDED**. Must not be required for a single-site MVP.

Sync: observations/events upload when WAN exists; local buffer on WAN loss.

## Containers

Compose is useful once there is an app to run; it is not a prerequisite for the first API. Kubernetes is out of scope until an ADR.

Secrets: `.env` locally; vault in production **PLANNED**.
