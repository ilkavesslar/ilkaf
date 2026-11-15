# Git branch governance

**Status:** Policy **IMPLEMENTED** in docs and agent rules. Remote `main`, `develop`, and `feature/sprint-0-foundation` **exist** on `origin`. Intended GitHub default branch: **`main`**.

Canonical integration branch name is **`develop`** (not `development` until an ADR).

## Required topology

```text
main          # protected; human merge only; GitHub default
 └── develop  # integration
      └── feature/* | fix/* | refactor/* | experiment/* | docs/ | test/ | chore/
```

Normal development flow:

```text
feature/*
    ↓ Pull Request
develop
    ↓ Pull Request
main
```

Agents must not: merge to `main`, push without a human request, force-push, delete remotes, or treat a long-lived `feature/*` branch as `develop`. Do not develop directly on `main`.

## Current repository (as of Sprint 0.5)

| Ref | State |
| :--- | :--- |
| `main` | Exists locally and on `origin`. Intended default branch. Tip: `2a30dc7` (`feat: harden foundation for sprint 0.5`). |
| `develop` | Exists locally and on `origin`. Integration branch. Currently same tip as `main` (`2a30dc7`). |
| `feature/sprint-0-foundation` | Exists locally and on `origin`. Sprint 0 / 0.5 foundation branch. Currently same tip as `main` / `develop` (`2a30dc7`). |

Sprint 0.5 foundation hardening is on these tips. New Sprint 1 work must use a **new** `feature/*` (or `fix/*`, etc.) branched from `develop`, not commits on `main`.

## Human-only remaining actions

Agents must not perform these (they require GitHub admin and/or explicit human approval):

1. Set GitHub default branch to `main` if it is not already.
2. Protect `main`: require pull request, dismiss stale reviews, no force-push, no deletion.
3. Prefer protecting `develop` the same way (PR-only integration).
4. Point `origin/HEAD` at `main` if it still references another branch.

CI already triggers on `main`, `develop`, `feature/**`, and pull requests (`.github/workflows/ci.yml`). It does not use Neon credentials.
