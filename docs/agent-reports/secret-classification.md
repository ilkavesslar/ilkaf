# Secret classification (Sprint 0.5)

| Item | Class | Action |
| :--- | :--- | :--- |
| `.env` | Secret file | Gitignored; never commit |
| `.env.example` empty `DATABASE_URL`, `OIDC_*`, `JWT_SECRET`, `SENTRY_DSN` | Template | OK in git |
| Compose `ilka_dev_only` | Local **placeholder** password | OK in git as documented non-production only |
| Alembic.ini `USER:PASSWORD@HOST` | Placeholder | OK in git |
| Neon connection strings | Secret | `.env` only; never CI logs |
| Camera/RTSP URLs | Secret (future) | Not present |

No production credentials were added this sprint.
