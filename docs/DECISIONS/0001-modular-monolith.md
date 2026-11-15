# ADR 0001: Modular monolith first

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

ILKA will grow cameras, CV, alerts, and multi-site features. Microservices would add ops cost before any runtime exists.

## Decision

Ship a modular monolith: `frontend/`, `backend/`, `cv/`, `ai/` as modules. Extract services only with a new ADR (scale, isolation, team, reliability).

## Consequences

Simpler Phase 1. Clear folders prevent a ball of mud if boundaries are enforced in review.
