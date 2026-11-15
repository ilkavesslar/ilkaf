# Cursor configuration for ILKA

This directory holds **shared** agent rules and skills. Local scratch stays gitignored.

## MCP servers (do not duplicate)

Official Cursor marketplace plugins are already enabled. Do **not** add the same servers here with API tokens. `.cursor/mcp.json` stays empty so plugins are not duplicated.

| Capability | Implementation | Access (actual) | Safest config |
| :--- | :--- | :--- | :--- |
| GitHub | Plugin `github` | Read/write API including merge/delete tools | Agents must not merge to `main`, delete repos, or force-push. Human-only merge. |
| Playwright | Plugin `playwright` | Browser automation | Dev/test URLs only (`localhost`, staging). No production destructive workflows. |
| Neon PostgreSQL | Plugin `neon` | **Write/destructive tools currently exposed** | Official read-only: OAuth **without** Full access, or URL `https://mcp.neon.tech/mcp?readonly=true`. The marketplace plugin does not expose a project-level toggle in this repo. Do not add a second Neon server. Until the plugin is read-only, treat all writes as human-gated. |
| Sentry | Plugin `sentry` | Diagnose errors | **needsAuth**. No SDK. No DSN in git. |
| Filesystem | Cursor native | Workspace files | No tree deletes / `.git` wipes without explicit human approval. |
| Git | Native + GitHub plugin | Local VCS | No history rewrite, no `main` merge. |

### Restrict Neon (manual)

1. Cursor Settings → MCP → Neon.
2. Prefer re-authenticate and leave **Full access** unchecked, **or** if the URL is editable, use `https://mcp.neon.tech/mcp?readonly=true`.
3. Do not paste Neon API keys into git.

`run_sql` in read-only mode must stay SELECT/EXPLAIN only.

## Always-on rules

Intentional `alwaysApply`: master, architecture, security, git-workflow, multi-agent (5). Other rules are glob-scoped.

## Agent roles (Cursor skills — do not duplicate as extra MCP)

| Role | Skill | Default implementation? |
| :--- | :--- | :--- |
| Architect | `ilka-architect` | No |
| Builder | `ilka-builder` | **Yes** |
| QA + Security | `ilka-qa-security` | No |
| AI/CV | `ilka-ai-cv` | No |

Also: `ilka-tester`, `ilka-reviewer` (Codex format), `ilka-debugger`, `ilka-claude-codex-workflow`.

Handoff and matrix: `docs/DEVELOPMENT-WORKFLOW.md`.
