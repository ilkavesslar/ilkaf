# Playwright E2E (foundation)

**Status:** Patterns only. There is no running ILKA UI, so these journeys cannot pass today.

## Tooling

- **Cursor Playwright MCP** (official plugin): use for exploratory and agent-driven browser checks against a future local URL (likely Vite `5173` or `3000` per `.env.example`).
- **In-repo `@playwright/test`:** not installed. Do not add Node dependencies until `frontend/` has a real app. Then add Playwright as a devDependency of the frontend or a dedicated `tests/e2e` package.

## Critical journeys (implement when UI exists)

| ID | Flow | Notes |
| :--- | :--- | :--- |
| AUTH-01 | Login success / failure | No auth UI yet |
| AUTH-02 | Session expiry / logout | |
| DASH-01 | Dashboard loads for allowed role | |
| NAV-01 | Primary navigation | |
| CAM-01 | Camera list and detail | |
| INC-01 | Incident list, detail, filters, search | |
| ALT-01 | Alert appear / acknowledge | |
| EMP-01 | Employee management (authorized only) | |
| SITE-01 | Site management | |
| TWIN-01 | Digital twin view | |
| FORM-01 | Create/update forms validation | |
| TBL-01 | Tables sort/page | |
| NOT-01 | Notifications | |
| RBAC-01 | Forbidden routes for Operator vs Admin vs Auditor | |

Reusable helpers (selectors, auth storage) belong in `tests/e2e/helpers/` once Playwright test runner is added.

Agents must drive **user flows**, not only compilation.
