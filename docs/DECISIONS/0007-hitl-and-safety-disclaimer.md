# ADR 0007: HITL and safety disclaimer

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

ILKA monitors industrial sites. Operators may over-trust dashboards. Software outages can look like “no hazards.”

## Decision

Safety-critical and punitive actions require human verification (or a documented automatic policy with audit). Monitoring/camera/model failure must be observable. Documentation and UI must not claim ILKA guarantees physical safety or replaces interlocks/procedures.

## Consequences

Product copy, alerts, and incident states need “candidate” vs “verified.” Blind-spot alerts are mandatory in the camera design.
