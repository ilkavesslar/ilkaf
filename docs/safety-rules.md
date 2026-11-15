# Safety rules (conceptual)

**Status:** **PLANNED**. These definitions are product intent for later sprints. Sprint 1 does **not** implement detection, tracking, or alerting.

ILKA will observe factory camera feeds and raise safety events for operator review. Computer-vision outputs are probabilistic. Punitive or compliance actions require a human in the loop.

### PPE

A violation may occur when required personal protective equipment is missing, for example a helmet, safety vest, or gloves in a zone that requires them.

### Restricted zone

A violation may occur when a person enters a configured restricted area (for example a vehicle lane, robot cell, or exclusion perimeter).

### Person–vehicle proximity

A hazard may occur when a person and a vehicle remain within a configured unsafe distance or overlapping zone for a defined duration.

### What is not decided here

Thresholds, model classes, zone geometry, and alert routing are specified in later sprints. Do not treat this file as an executable rule engine.
