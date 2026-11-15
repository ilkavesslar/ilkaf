# Development workflow (Hybrid Agile + four agents)

**Status:** Process defined. Sprint 0 API/UI foundation **IMPLEMENTED**. Cameras/CV/login **not** implemented.

## Four Cursor agents

| Agent | Skill | Default? | Typical activation |
| :--- | :--- | :--- | :--- |
| Architect | `ilka-architect` | No | Requirements, ADRs, contracts, new modules |
| **Builder** | `ilka-builder` | **Yes (implementation)** | Approved coding, tests, refactors, fixes |
| QA + Security | `ilka-qa-security` | No | After impl, before merge, security |
| AI/CV | `ilka-ai-cv` | No | Cameras, video, models, detection pipeline |

Supporting (do not duplicate the four): `ilka-tester` (test execution), `ilka-reviewer` (Codex finding format), `ilka-debugger` (non-prod RCA).

Cursor is the implementation environment. **Codex** is an independent reviewer. **Claude** is an extra reasoning/review layer for architecture, CV, and UX.

## Responsibility matrix

| Area | Architect | Builder | QA/Security | AI/CV |
| :--- | :--- | :--- | :--- | :--- |
| Requirements | Primary | Support | Review | Support |
| Architecture | Primary | Follow | Review | Review |
| Backend | Design | Primary | Review | Support |
| Frontend | Design | Primary | Review | Support |
| Database | Design | Implement | Review | Support |
| Security | Design | Implement | Primary | Review |
| Testing | Define | Implement | Primary | AI-specific |
| Camera | Design | Implement | Review | Primary |
| Computer Vision | Review | Integration | Review | Primary |
| AI Models | Review | Integration | Validate | Primary |
| Deployment | Design | Implement | Validate | AI/Edge |
| ADRs | Primary | Contribute | Review | Contribute |

## Source of truth

Authoritative: `PROJECT-OVERVIEW.md`, `REQUIREMENTS.md`, `ARCHITECTURE.md`, `SYSTEM-ARCHITECTURE.md`, `CAMERA-ARCHITECTURE.md`, `AI-PIPELINE.md`, `EVENT-ARCHITECTURE.md`, `SECURITY-ARCHITECTURE.md`, `DATABASE-ARCHITECTURE.md`, this file, `TESTING-STRATEGY.md`, `ROADMAP.md`, `docs/DECISIONS/`.

**If documents conflict: do not guess. Request an ADR.**

Known conflict: integration branch name `develop` ([CONTRIBUTING.md](../CONTRIBUTING.md), existing rules) vs `development` (some workflow drafts). **Until an ADR, use `develop`.**

## Handoff (major features)

1. **Architect** — objective, requirements, modules, architecture, contracts, security, tests, plan (`docs/agent-reports/architecture-review.md` if non-trivial).  
2. **Builder** — inspect, implement, tests, report files (`implementation-report.md`). One feature branch; no parallel blind edits.  
3. **QA/Security** — inspect, test, severity findings (`qa-report.md`). No prod-code edits unless asked.  
4. **AI/CV** — only if camera/video/CV (`ai-cv-review.md`). Must not treat predictions as incidents.  
5. **Independent** — Codex (`CODEX.md`); Claude when architecture/CV/UX is heavy. They must not rubber-stamp Cursor.  
6. **Builder** — accepted fixes.  
7. **QA** — retest.  
8. **Human** — merge.

## Git

```text
main
 └── develop          # canonical integration branch (not "development" until ADR)
      ├── feature/*
      ├── fix/*       # alias: bugfix/, CONTRIBUTING fix/
      ├── refactor/*
      └── experiment/*
```

Also `feat/`, `docs/`, `test/`, `chore/` per CONTRIBUTING. Human merge to `main`. Agents do not merge, force-push, or delete repos.

If `main` or `develop` is missing on the remote, follow [`GIT-GOVERNANCE.md`](./GIT-GOVERNANCE.md) (human-only to create/protect). Do not treat `feature/sprint-0-foundation` as the integration branch.

## Conflict prevention

Do not overwrite others blindly; delete features without justification; change architecture without ADR; change schema without a migration plan; change APIs without docs; install unjustified deps; mishandle secrets; disable tests; weaken security to unblock; fabricate green tests. If you find incomplete work: **stop and inspect**.

## Reports

Non-trivial only, under [agent-reports/](./agent-reports/): objective, files inspected/changed, decisions, tests, unresolved, risks, next action.

## Sprint rules

One slice per sprint; no fake features; CV/cameras after identity, tenancy, and audit ([ROADMAP.md](./ROADMAP.md)).
