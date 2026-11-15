# E2E selector and auth patterns

Use stable `data-testid` attributes in the future UI. Do not select by CSS class or copy that will change.

Suggested testids (not implemented in the app):

- `login-email`, `login-password`, `login-submit`
- `nav-dashboard`, `nav-cameras`, `nav-incidents`, `nav-alerts`, `nav-employees`, `nav-sites`, `nav-twin`
- `incident-table`, `incident-search`, `incident-filter-status`
- `alert-banner`, `alert-acknowledge`
- `camera-grid`, `camera-tile`

Auth pattern (when login exists):

1. Log in via UI once per role fixture (operator, safety_officer, admin, auditor).
2. Persist storage state per role (Playwright `storageState`).
3. Never commit session cookies or passwords. Use env: `E2E_USER_OPERATOR`, `E2E_PASSWORD` in local `.env` only.
