# Authentication (custom ILKA)

**Status:** Custom authentication skeleton is **SCAFFOLDED** (Phase 1C). Full credential authentication is **NOT YET IMPLEMENTED**.

Auth0/OIDC integration has been removed. ILKA now manages its own authentication layer. Authorization (roles, organization scope, site access) remains unchanged.

```text
Browser / Frontend
        |
        v
POST /api/v1/auth/login
        |
        v
ILKA backend validates email/password (future)
        |
        v
Session token (short-lived) + refresh token (server-side, future)
        |
        v
ILKA API validates session token
        |
        v
Resolve provisioned User and build Principal
        |
        v
RBAC enforces organization/site/permission boundaries
```

## Configuration

Environment variables (see `.env.example`):

| Variable | Purpose |
| :--- | :--- |
| `AUTH_SECRET_KEY` | Secret used to sign session tokens. Required in production. Must be at least 32 bytes. |
| `AUTH_ALGORITHM` | HMAC signing algorithm allowlist. Default `HS256`. `none` and non-HMAC algorithms are rejected. |
| `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime. Default `15`. |
| `AUTH_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime. Default `7`. |

Never commit real values. Never log access tokens, refresh tokens, or plaintext passwords.

## Current behavior

- `POST /api/v1/auth/login` returns **501 Not Implemented**.
- `POST /api/v1/auth/logout` returns **501 Not Implemented**.
- `GET /api/v1/auth/me` requires authentication and returns the current `Principal`.
- Protected routes (`/api/v1/me`, sites, cameras, demo observations, lab cameras) return **401** when no valid bearer token is supplied.
- The default production token validator fails closed with **401**.

## Identity resolution

When a valid session token is provided, the backend resolves the user by:

1. `users.id` if the token carries `user_id`.
2. Otherwise by `users.email` case-insensitively.

The user must be provisioned and not disabled. Site assignments are loaded from `user_site_assignments`.

## Frontend

`frontend/src/auth/AuthProvider.tsx` provides the authentication context:

- `status`: `loading` | `unauthenticated` | `authenticated`
- `login(email, password)`: submits credentials to `/api/v1/auth/login`
- `logout()`: clears client-side session state (server-side revocation is future work)
- `getAccessToken()`: returns a bearer token for API calls

`frontend/src/views/LoginView.tsx` is an ILKA-branded email/password form. It does not store the password after submission. Until the backend login endpoint is implemented, the UI displays an "Authentication setup in progress" message.

## Development and tests

Automated tests do not call an external IdP. They mint HMAC test tokens and inject a `TestTokenValidator` via `set_token_validator` (test-only). That hook is not a production bypass.

## Future work

- Add `password_hash`, `email_verified`, `failed_login_attempts`, and `locked_until` columns to `users`.
- Add a `user_sessions` table for refresh token revocation.
- Implement Argon2id password hashing.
- Implement login rate limiting and account lockout.
- Implement password reset, email verification, and MFA.
- Add structured audit logging for authentication events.
