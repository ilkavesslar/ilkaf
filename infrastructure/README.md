# Infrastructure & Deployment

## Responsibilities
- Container definitions (Docker, Docker Compose for local dev and edge nodes).
- Orchestration manifests (Kubernetes manifests for cloud ingestion/aggregation).
- Infrastructure as Code (Terraform) for provisioning cloud and edge infrastructure.
- Observability stack configs (Prometheus, Grafana, OpenTelemetry).

## Directory Layout (Planned)
```text
infrastructure/
├── docker/                 # Dockerfiles and Docker Compose profiles
├── k8s/                    # Helm charts and Kubernetes manifests
├── terraform/              # Cloud provisioning modules
└── monitoring/             # Prometheus alerting rules and Grafana dashboards
```
