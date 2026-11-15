# ADR 0003: Observations are not incidents

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

Collapsing detector output into “incident” causes false alarms and unsafe overconfidence.

## Decision

Keep separate stages: observation → detection → event → verification → incident → alert → action, all audited. HITL (or explicit policy) before punitive/high-severity confirmation.

## Consequences

More tables/types later; safer operations. See [AI-PIPELINE.md](../AI-PIPELINE.md).
