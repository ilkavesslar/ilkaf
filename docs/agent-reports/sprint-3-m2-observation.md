# Sprint 3 M2 — typed observation contract

**Agent:** Builder (with AI/CV contract rules)  
**Branch:** `feature/sprint-3-m2-observation`  
**Date:** 2026-09-20

## Status

Typed `BoundingBox` and `Observation` dataclasses are implemented in `cv/observation.py`. Detectors, persistence, and APIs were not added. Observations remain distinct from incidents (ADR 0003).

## Contract

- Normalized box `x_min/y_min/x_max/y_max` in `[0.0, 1.0]` with strictly positive area
- Confidence in `[0.0, 1.0]`, finite
- `media_timestamp` optional (source timeline); `observed_at` required UTC wall clock
- Default `[MOCK / SYNTHETIC]` via `is_synthetic` / `mock_label`

## Tests

`tests/unit/test_cv_observation.py`
