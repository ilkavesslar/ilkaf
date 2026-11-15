# Test Suites & Quality Assurance

## Responsibilities
- Automated test suites verifying functional and non-functional safety platform behaviors.
- Synthetic video and frame generation for deterministic CV testing.
- Simulation of network dropouts, reconnection bursts, and high-concurrency event ingestion.

## Directory Layout (Planned)
```text
tests/
├── unit/                   # Fast, isolated unit tests for backend, CV geometry, AI scoring
├── integration/            # Multi-service integration (DB + Backend + Event Bus)
├── cv_ai/                  # Deterministic visual benchmarks & confusion matrix assertions
├── e2e/                    # End-to-end browser/WebSocket tests (Playwright patterns; runner not installed yet)
└── performance/            # Load tests, stream saturation, and latency profiling
```
