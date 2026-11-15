# Observability

**Status:** **PLANNED**. No metrics stack **IMPLEMENTED**.

ILKA must not fail silent. Distinguish at least:

| Condition | Meaning |
| :--- | :--- |
| System unavailable | API/UI down |
| Monitoring degraded | Partial cameras or delayed events |
| Detection unavailable | Models/workers down; streams may still record later |
| Camera unavailable | That camera has no fresh frames |
| Alert delivery failure | Incident exists but operators were not notified |

## Before production

Structured JSON logs (UTC, service, severity, correlation id). **Never** log secrets or RTSP passwords.

Health: liveness (process), readiness (DB reachable).

When cameras exist: last-frame age, reconnect count, ingest FPS, inference latency, queue depth, drop counts, event lag, alert ack latency, CPU/GPU/disk, error rates.

Tracing: **PROVISIONAL** after there is more than one process.

Sentry: optional after DSN; plugin not authenticated. Prometheus/Grafana **NOT DECIDED**.

Health checks are part of the product, not an afterthought.
