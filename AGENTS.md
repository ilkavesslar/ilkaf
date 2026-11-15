# Multi-Agent Engineering Constitution & Rules (AGENTS.md)

This document establishes the binding engineering constitution and operational rules for all AI coding agents (including Antigravity, Cursor, and OpenAI Codex) and human engineers working on **ILKA — Industrial Safety Platform**.

---

## 1. Core Engineering Principles

### Principle 1: Inspect Before Modifying
- Always inspect the workspace, related modules, configuration files, and existing tests before proposing or making changes.
- Never make blind assumptions about dependencies, schemas, endpoints, or file paths.

### Principle 2: Plan Before Implementing
- Major features, schema adjustments, interface changes, or architectural shifts require an approved Implementation Plan before code execution.
- Detail the rationale, blast radius, dependencies, and verification strategy in the plan.

### Principle 3: Modular Architecture & Separation of Concerns
- Strictly enforce domain boundaries:
  - `frontend/`: UI components, dashboard visualizations, WebSocket subscriptions, client state.
  - `backend/`: Core business logic, domain models, RBAC enforcement, REST/WebSocket APIs, event dispatching.
  - `cv/`: RTSP stream ingestion, frame decoders, edge inference wrappers, tracking, spatial geometry.
  - `ai/`: Anomaly scoring, temporal aggregation, pattern recognition, explainability metadata.
  - `database/`: Schema migrations, DDL definitions, seed datasets, connection pooling.
  - `infrastructure/`: Containerization, orchestration manifests, infrastructure-as-code, observability.
  - `tests/`: Automated unit, integration, end-to-end, performance, and CV/AI benchmark suites.
  - `scripts/`: Tooling, development bootstrap, validation scripts.
- Cross-boundary communication must use explicit, strongly-typed contracts (e.g., Pydantic schemas, TypeScript interfaces, OpenAPI specifications).

### Principle 4: Secure Coding & No Hard-Coded Secrets
- Never hard-code credentials, private keys, API tokens, database connection strings, or camera credentials in code or version control.
- All secrets must be loaded from environment variables defined in `.env` (templated in `.env.example`).
- Enforce strict input validation, type checking, and sanitization on all ingress points (REST, WebSockets, RTSP metadata).

### Principle 5: Proper Error Handling & Fail-Safe Behavior
- Systems must always fail safely (fail-safe posture). A failure in one video stream, detector, or background worker must never crash the service or silently drop alerts.
- Never suppress exceptions with bare `except: pass` or unhandled promise rejections.
- Log failures with full diagnostic context and structured error payloads.

### Principle 6: Managed Database Migrations
- Never perform unversioned DDL modifications or destructive ad-hoc database updates.
- All schema transitions must be versioned, reversible, and forward/backward compatible.

### Principle 7: Automated Testing & Verification
- Every new feature, bug fix, or refactor must be accompanied by automated tests.
- Code without tests is incomplete and must not be marked ready for production.

### Principle 8: Structured Logging & Observability
- All events, state changes, security checks, and operator actions must generate structured JSON logs.
- Include standard correlation IDs, timestamps (UTC ISO 8601), user/service identities, and component tags.

### Principle 9: Backwards Compatibility & Minimal Dependencies
- Maintain interface and API backwards compatibility.
- Do not introduce external libraries or dependencies without explicit justification and architectural need.

### Principle 10: Zero Destructive Operations Without Explicit Approval
- Never execute unverified bulk deletions, database drops, table wipes, or destructive file overwrites without explicit human authorization.

### Principle 11: No Fabricated Data Presented as Real
- Never present dummy mocks, synthetic telemetry, or simulated detections as real production data without explicit `[MOCK / SYNTHETIC]` labeling.
- Production pathways must strictly consume validated, real-world data sources.

### Principle 12: Probabilistic AI/CV Handling & Human Verification
- AI/CV outputs are probabilistic observations, never infallible facts.
- All detection events must carry confidence scores, model provenance, and bounding/polygon metadata.
- Safety-critical operations and punitive compliance actions must mandate human-in-the-loop (HITL) operator verification.

---

## 2. Agent Roles & Responsibilities

| Role | Agent / Tool | Responsibilities |
| :--- | :--- | :--- |
| **Cursor — Architect / Builder / QA-Security / AI-CV** | `.cursor/skills/ilka-*` | Plan, implement, in-repo QA, CV (see `docs/DEVELOPMENT-WORKFLOW.md`) |
| **Independent Adversarial Reviewer** | **OpenAI Codex** | `CODEX.md` / `ilka-reviewer` — must not rubber-stamp Cursor |
| **Additional reasoning / review** | **Claude** | Architecture, CV, UX when the change is heavy |

---

## 3. Operational Workflow for All Agents

```text
[Requirement / Task]
       │
       ▼
[Phase 1: Workspace Inspection & Research]
       │
       ▼
[Phase 2: Implementation Plan Formulation]
       │
       ▼
[Phase 3: Independent Review (Codex) & Alignment]
       │
       ▼
[Phase 4: Modular & Typed Implementation]
       │
       ▼
[Phase 5: Automated Verification & Test Execution]
       │
       ▼
[Phase 6: Audit, Review & Human Lead Approval]
```

---

## 4. Cursor project rules and agent roles

Shared Cursor rules: `.cursor/rules/`. Shared role skills: `.cursor/skills/`. MCP inventory: `.cursor/README.md`. Documentation map: [`docs/README.md`](./docs/README.md).

Do not duplicate GitHub, Neon, Playwright, or Sentry MCP servers in `.cursor/mcp.json` (those are Cursor plugins).

### Cursor role skills

| Skill | May do | Must not |
| :--- | :--- | :--- |
| Architect | Plans, ADRs, contracts | Large code unless explicitly authorized |
| Builder | Implementation + tests | Production deploys, secret commits |
| Tester | Tests and reproduction | Fake-green E2E |
| Debugger | Root cause + non-prod fixes | Production data changes |
| Reviewer | Read-only review | Merge, silent code edits |

### Forbidden for every agent

Delete the repository; reset Git history; drop a database; modify production data; expose secrets; merge to `main`; deploy production without human approval; Neon `DROP`/`TRUNCATE`/destructive MCP tools without an explicit human request.


