# Contributing to ILKA (CONTRIBUTING.md)

This document establishes the mandatory engineering lifecycle and contribution standards for all engineers and AI agents contributing to the ILKA platform.

---

## 1. Development Lifecycle & Engineering Workflow

Every change—whether a feature, refactor, or bug fix—must progress through this strict 10-step lifecycle:

```text
1. Requirement Specification
   │ (Define problem in docs/requirements/)
   ▼
2. Architecture & Contract Design
   │ (Define schemas, DTOs, and ADR in docs/architecture/)
   ▼
3. Implementation Plan
   │ (Formulate plan covering affected modules and test strategies)
   ▼
4. Development
   │ (Write modular, strictly typed code adhering to AGENTS.md)
   ▼
5. Automated Tests
   │ (Write unit, integration, or benchmark tests in tests/)
   ▼
6. Independent Codex Review
   │ (Codex performs adversarial evaluation per CODEX.md)
   ▼
7. Fixes & Remediation
   │ (Address all CRITICAL, HIGH, and MEDIUM findings)
   ▼
8. Re-review
   │ (Verify all remediation steps and regression tests pass)
   ▼
9. Human Lead Approval
   │ (Human Engineering Lead reviews and signs off on the change)
   ▼
10. Git Commit & Merge (never by an agent into `main`)
     (Commit using Conventional Commits standard)
```

Quality gates (must all pass conceptually): [`docs/QUALITY_GATES.md`](./docs/QUALITY_GATES.md).

---

## 2. Branching Strategy

- **`main`**: Production-ready. Direct commits prohibited. Human approval to merge.
- **`develop`**: Integration branch (canonical name; not `development` until an ADR).
- **Work branches** (either style is acceptable):
  - `feature/<scope>-<description>` or `feat/<scope>-<description>`
  - `bugfix/<scope>-<description>` or `fix/<scope>-<description>`
  - `refactor/<scope>-<description>`
  - `docs/…`, `test/…`, `chore/…` as needed

`feature/*` branches are not substitutes for `develop`. Current remote topology and the human-only steps to create `main` / `develop` are in [`docs/GIT-GOVERNANCE.md`](./docs/GIT-GOVERNANCE.md). Agents must not push, merge to `main`, or create those protected branches.


---

## 3. Commit Message Conventions

Commit messages must follow the **Conventional Commits** specification:

```text
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

### Allowed Types:
- `feat`: New feature or capability.
- `fix`: Bug fix.
- `docs`: Documentation updates.
- `refactor`: Code refactoring without functional changes.
- `test`: Adding or modifying automated test suites.
- `chore`: Tooling, configuration, or maintenance changes.
- `security`: Security enhancements or vulnerability remediations.

### Examples:
- `feat(cv): implement bounded ring buffer for RTSP frame ingestion`
- `fix(backend): enforce supervisor permission on safety policy update`
- `test(ai): add negative test for zero-confidence detection payload`

---

## 4. Code Review Standards

1. **Self-Inspection**: Before requesting review, inspect diffs for accidental secrets, debug logs, or commented-out code.
2. **Automated Verification**: Ensure all linters, type checkers (`mypy`, `tsc`), and test runners pass.
3. **Adversarial Audit**: Every significant change must be subjected to independent review per [`CODEX.md`](./CODEX.md).
