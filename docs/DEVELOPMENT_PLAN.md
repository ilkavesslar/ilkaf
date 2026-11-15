# Development plan

**Status:** Foundation **SCAFFOLDED**. Phase 1 implementation **not started**.

Roadmap sketch: `docs/plans/README.md` (treat FastAPI/CV phases as **PLANNED**, FastAPI **PROVISIONAL**).

## Git workflow

```text
main          # protected; human merge only
  ↑
develop       # integration
  ↑
feature/*     # (alias: feat/ from CONTRIBUTING.md)
bugfix/*      # (alias: fix/)
refactor/*
```

Also allowed: `docs/`, `test/`, `chore/` per `CONTRIBUTING.md`.

Never commit to `main` directly. Agents must not merge PRs or delete branches.

Quality gates before merge: `docs/QUALITY_GATES.md`. PR checklist: `.github/PULL_REQUEST_TEMPLATE.md`.

## GitHub readiness (this clone)

Verified previously: local `main`, **no commits**, **no remote**, GitHub MCP user may exist while **this repo is not on GitHub**.

Do **not** let an agent create the GitHub repository unless you name the owner/org.

### Manual steps

1. On GitHub, create an **empty** private repository (no README/license if this tree already has them).
2. Confirm `.env` is not present or is gitignored. Never add secrets.
3. First commit locally (you or an agent **only if you ask**).
4. `git remote add origin https://github.com/<OWNER>/<REPO>.git`
5. `git push -u origin main`
6. `git checkout -b develop && git push -u origin develop`
7. Settings → Branches: protect `main` (PR required, no admin bypass if possible, no force-push).
8. Optional: require CI later when tests exist.

## GitHub / Neon (ops)

See this file for connect steps. Product phases: [ROADMAP.md](./ROADMAP.md). Process: [DEVELOPMENT-WORKFLOW.md](./DEVELOPMENT-WORKFLOW.md).

Modular monolith: UI + API + Neon **dev**. Domain slice: User, Role, Site, AuditLog. No CV/Redis/Docker requirement.

| Phase | Intent | Status |
| :--- | :--- | :--- |
| 0 Foundation | Layout, agents, Cursor, docs | **SCAFFOLDED** |
| 1 Contracts + first slice | Auth/site/audit against Neon | **PLANNED** |
| 2+ CV/AI/cameras | Separate modules, not extra services | **PLANNED** |
