# Digital twin

**Status:** **PLANNED**. Hierarchy is a design intent, not an **IMPLEMENTED** map. Mapping library **NOT DECIDED**.

## Hierarchy

Site → Building → Floor → Zone → Camera/Sensor → Safety Event

## Planned capabilities

Spatial mapping, zone polygons, camera locations, live status, incidents, historical events.

Storage should be PostgreSQL (versioned migrations) plus frontend visualization **TODO**. Coordinate CRS and indoor mapping library are **DECISION REQUIRED**.
