# ADR 0011: ILKA-managed custom authentication

- **Status:** Accepted (Skeleton — Phase 1C)
- **Date:** 2026-11-05
- **Supersedes:** [ADR 0010: Hybrid OIDC identity + ILKA authorization records](./0010-hybrid-oidc-authorization.md)

## Context

ILKA is a B2B industrial safety platform. The platform provider (ILKA) manages customer Organizations. Each Organization has its own users, sites, and cameras. SYSTEM_ADMIN users belong to the ILKA platform team and provision Organizations. ORG_ADMIN users manage users within their own Organization. Public self-registration is not allowed.

The previous decision (ADR 0010) used an external OIDC identity provider (Auth0) for authentication and ILKA database records for authorization. Product and operational requirements now require ILKA to own the entire authentication layer so that customer onboarding, user lifecycle, and access control are managed inside the platform.

## Decision

- **Authentication** (who the human is): ILKA-managed email/password authentication with sessions signed by a platform-controlled secret.
- **Authorization** (what they may do): unchanged — ILKA database roles, organization scoping, and site assignments remain authoritative.
- **Password storage**: Argon2id hashes only. Plaintext passwords are never stored or logged.
- **Sessions**: short-lived access tokens plus longer-lived, server-tracked refresh tokens. Logout revokes the refresh token and drops the access token on the client.
- **SSO future**: the schema keeps room for future federated identity re-integration, but the default path is ILKA-managed credentials.

## Skeleton scope

Phase 1C intentionally creates only interfaces and placeholders:

- `app.core.auth` — session token validator interface (currently fails closed).
- `app.core.password` — password hasher interface (currently a placeholder).
- `app.services.auth_service` — credential authentication and session management placeholders.
- `app.api.auth` — `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/auth/me` returning HTTP 501 where not yet implemented.
- `frontend/src/auth/*` — custom React context, provider, and login view without Auth0.

Real password verification, session persistence, Argon2id wiring, email verification, password reset, MFA, and audit logging are follow-up work.

## Security implications

- The skeleton cannot be used to bypass authentication: protected routes fail 401 when no valid session is supplied.
- No custom cryptography is introduced; a vetted Argon2id library will be added later.
- Secrets (`AUTH_SECRET_KEY`, database credentials, email credentials) are loaded from environment variables and never committed.
- HTTPS is required for production login and authenticated traffic.
- Audit logging will record authentication events once the implementation is complete.

## Consequences

- Auth0 and OIDC configuration, packages, and tests are removed.
- Existing RBAC, organization boundaries, and site-level authorization are preserved.
- A migration is needed to add password/session columns and tables before full implementation.
