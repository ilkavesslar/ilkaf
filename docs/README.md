# Documentation index

ILKA docs use these status labels: **IMPLEMENTED** · **SCAFFOLDED** · **PLANNED** · **PROVISIONAL** · **NOT DECIDED**.

Authoritative ADRs: [`DECISIONS.md`](./DECISIONS.md) and [`DECISIONS/`](./DECISIONS/).

| Topic | Canonical file | Notes |
| :--- | :--- | :--- |
| Overview | [PROJECT-OVERVIEW.md](./PROJECT-OVERVIEW.md) | Also root `README.md` |
| Requirements | [REQUIREMENTS.md](./REQUIREMENTS.md) | Detail: `requirements/README.md` |
| Current vs Phase 1 | [ARCHITECTURE.md](./ARCHITECTURE.md) | |
| Target system | [SYSTEM-ARCHITECTURE.md](./SYSTEM-ARCHITECTURE.md) | |
| Cameras / video | [CAMERA-ARCHITECTURE.md](./CAMERA-ARCHITECTURE.md) | |
| AI / CV pipeline | [AI-PIPELINE.md](./AI-PIPELINE.md) | Models: `AI_MODELS.md` |
| Human Intelligence Engine | [HUMAN-INTELLIGENCE.md](./HUMAN-INTELLIGENCE.md) | ADR 0012; contract 1.0.0 |
| HIE models / datasets | [models/HUMAN_INTELLIGENCE_MODELS.md](./models/HUMAN_INTELLIGENCE_MODELS.md) | Registry + licensing |
| Intel Mac / NVIDIA profiles | [deployment/INTEL_MAC_AND_NVIDIA.md](./deployment/INTEL_MAC_AND_NVIDIA.md) | CUDA unverified without GPU |
| HIE performance report | [agent-reports/human-intelligence-performance.md](./agent-reports/human-intelligence-performance.md) | Measured vs unverified |
| HIE security/privacy | [agent-reports/human-intelligence-security-privacy.md](./agent-reports/human-intelligence-security-privacy.md) | Anonymous-by-default |
| Events | [EVENT-ARCHITECTURE.md](./EVENT-ARCHITECTURE.md) | Redis **not** selected |
| Security | [SECURITY-ARCHITECTURE.md](./SECURITY-ARCHITECTURE.md) | Root `SECURITY.md` baseline |
| Data | [DATABASE-ARCHITECTURE.md](./DATABASE-ARCHITECTURE.md) | Phase-1 fields: `DATABASE_SCHEMA.md` |
| Deploy / hybrid | [DEPLOYMENT-ARCHITECTURE.md](./DEPLOYMENT-ARCHITECTURE.md) | |
| Observability | [OBSERVABILITY.md](./OBSERVABILITY.md) | |
| Hardware | [HARDWARE-REQUIREMENTS.md](./HARDWARE-REQUIREMENTS.md) | No SKUs locked |
| Process | [DEVELOPMENT-WORKFLOW.md](./DEVELOPMENT-WORKFLOW.md) | Four agents, handoff, Git |
| Git branches | [GIT-GOVERNANCE.md](./GIT-GOVERNANCE.md) | `main` / `develop` policy; human-only topology |
| Agent reports | [agent-reports/](./agent-reports/) | Non-trivial handoffs |
| Tests | [TESTING-STRATEGY.md](./TESTING-STRATEGY.md) | |
| Roadmap / sprints | [ROADMAP.md](./ROADMAP.md) | |
| Quality gates | [QUALITY_GATES.md](./QUALITY_GATES.md) | |
| Auth | [authentication.md](./authentication.md) / [authorization.md](./authorization.md) | Custom ILKA auth + RBAC (Sprint 3 skeleton) |
| Local runbook | [DEVELOPMENT.md](./DEVELOPMENT.md) | Install, start, test (same as `development.md` on Windows) |
| Developer startup | [development/startup.md](./development/startup.md) | First-time + daily three-terminal workflow |
| Intel Mac CV setup | [development/mac-setup.md](./development/mac-setup.md) | Separate app vs `.venv-cv` Torch pins |
| Safety rules (conceptual) | [safety-rules.md](./safety-rules.md) | PPE / zone / proximity intent; not implemented |
| Digital twin | [DIGITAL_TWIN.md](./DIGITAL_TWIN.md) | |

Older filenames (`CAMERA_ARCHITECTURE.md`, `SECURITY.md` under `docs/`, etc.) are short pointers to the canonical files above.
