# Quality Assurance & Testing Strategy (docs/testing)

This document establishes the multi-tiered testing strategy for the ILKA platform.

---

## 1. Test Pyramid & Quality Gates

```text
               / \
              /   \
             / E2E \           (Full browser, WebSocket & simulated stream flows)
            /───────\
           / Security\         (RBAC audits, fuzzing, token tests)
          /───────────\
         / Performance \       (Multi-stream load, frame buffer saturation)
        /───────────────\
       /   Integration   \     (DB, Redis, API, and WebSocket message bus)
      /───────────────────\
     / AI/CV Model Eval    \   (Confusion matrix, synthetic frame benchmarks)
    /───────────────────────\
   /        Unit Tests       \ (Domain models, geometric algorithms, handlers)
  /───────────────────────────\
```

---

## 2. Test Categories & Execution Scope

### 2.1 Unit Tests (`tests/unit/`)
- **Scope**: Core domain business logic, spatial geometry calculations (point-in-polygon, IoU), timestamp parsing, Pydantic/Zod schema validators, state machine transitions.
- **Requirement**: Fast, in-memory execution; zero external network dependencies. Minimum target coverage: 85%.

### 2.2 Integration Tests (`tests/integration/`)
- **Scope**: REST endpoints against a test PostgreSQL instance (via test containers or async rollback), Redis Stream publish/subscribe fan-out, WebSocket connection lifecycles.
- **Requirement**: Test database transactions rolled back after each test case.

### 2.3 API Contract Tests (`tests/integration/api/`)
- **Scope**: OpenAPI specification validation, response status code verification, error envelope schema assertions.

### 2.4 Frontend Tests (`frontend/`)
- **Scope**: Component rendering (React Testing Library / Vitest), state hook behaviors, alert notification badges, modal interactions.

### 2.5 End-to-End Tests (`tests/e2e/`)
- **Scope**: Complete user journeys: User logs in → Subscribes to live camera → Simulated hazard occurs → Candidate alert pops up on dashboard → Operator acknowledges & verifies alert → Audit log persists.

### 2.6 Security & Access Control Tests (`tests/security/`)
- **Scope**: Unauthenticated access attempts to protected routes, privilege escalation probes across roles (e.g. Operator trying to change Safety Policy), injection payload testing.

### 2.7 Performance & Load Tests (`tests/performance/`)
- **Scope**: Ingestion saturation (simulating 10–50 concurrent RTSP camera feeds), frame dropping under artificial CPU limits, WebSocket client broadcast throughput.

### 2.8 AI / CV Model Evaluation Benchmarks (`tests/cv_ai/`)
- **Scope**: Deterministic synthetic video frame suites asserting precision, recall, confusion matrices, and confidence distributions on reference datasets.

### 2.9 Regression Testing
- **Scope**: Every resolved bug must be paired with an automated regression test reproducing the failure condition before the fix is applied.
