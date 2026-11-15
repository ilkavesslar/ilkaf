# Deployment & Infrastructure Architecture (docs/deployment)

> [!NOTE]
> **Status**: Planned Architecture Specification. Actual deployment pipelines and infrastructure provisioning will be implemented in subsequent phases.

---

## 1. Planned Deployment Environments

### 1.1 Development Environment
- **Target**: Local developer workstations.
- **Topology**: Docker Compose running PostgreSQL, Redis, backend API server, simulated RTSP stream generator, and Vite frontend dev server.
- **Data**: Synthetic mock cameras and seeded test database.

### 1.2 Staging / Pre-Production Environment
- **Target**: Dedicated staging cluster / test lab.
- **Topology**: Mirror of production topology with real RTSP test cameras and GPU inference nodes.
- **Purpose**: Load testing, continuous integration verification, security scanning, and adversarial validation.

### 1.3 Production Environment
- **Target**: Industrial plant edge gateways (on-premise) coupled with central cloud/on-prem management servers.
- **Edge Layer**: Edge compute nodes (x86/ARM with optional NVIDIA GPUs) processing local RTSP camera feeds and running detection models.
- **Central Management Layer**: Clustered backend services, PostgreSQL database with high availability replication, Redis cluster, and ingress gateways.

---

## 2. Operational Domains

### 2.1 Configuration Management
- Environment-specific settings managed via strictly validated configuration schemas.
- Infrastructure-as-Code (Terraform / Ansible) for provisioning reproducible compute, networking, and storage.

### 2.2 Secrets Management
- Production secrets managed via enterprise secret vaults (e.g., HashiCorp Vault, AWS Secrets Manager, or Kubernetes Secrets).
- Zero plaintext secrets in code, container images, or configuration files.

### 2.3 Database Migrations
- Automated, forward-and-backward compatible migrations executed as pre-deployment jobs (e.g., Alembic migrations in containers).
- Pre-migration database snapshots to ensure instantaneous rollback in case of migration failure.

### 2.4 Observability & Monitoring
- **Metrics**: Prometheus scraping service health, frame ingestion rates, detection latencies, and queue depths.
- **Dashboards**: Grafana visualizations for operational and infrastructure health.
- **Logging**: Centralized structured logging with retention and search capabilities.

### 2.5 Backups & Disaster Recovery
- Automated daily incremental and weekly full database backups.
- Regular disaster recovery drills with Recovery Time Objective (RTO < 1h) and Recovery Point Objective (RPO < 5min).
