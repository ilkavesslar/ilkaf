---
name: ilka-claude-codex-workflow
description: ILKA Cursor plus Claude plus Codex workflow. Use when deciding which agent should architect, implement, review, or verify a change.
---

# Claude + Codex workflow

Cursor is the primary environment: orchestration, repository navigation, implementation, and tool coordination.

- **Claude**: architecture, large features, UX reasoning, complex refactors — after a written plan.
- **Codex**: review, debugging, testing, correctness, refactor verification per `CODEX.md`.
- **GitHub plugin**: issues/PRs/Actions. Humans merge to `main`. Agents must not merge or delete repositories.
- **Neon plugin**: inspection only unless a human explicitly requests a named non-production write. Prefer `?readonly=true`. No production access.
- **Playwright MCP**: local/dev/staging operator journeys only.
- **Sentry plugin**: production diagnostics after auth and SDK exist.

Cursor implements (Builder by default). Independent review: **Codex** (`CODEX.md`, `ilka-reviewer`) must not rubber-stamp. **Claude**: architecture, CV, UX when useful. In-repo QA before merge: `ilka-qa-security`. Camera/CV design: `ilka-ai-cv`.

