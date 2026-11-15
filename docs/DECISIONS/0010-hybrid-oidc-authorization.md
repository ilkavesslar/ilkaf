# ADR 0010: Hybrid OIDC identity + ILKA authorization records

- **Status:** Superseded by [ADR 0011: ILKA-managed custom authentication](./0011-custom-authentication.md)
- **Date:** 2026-08-20
- **Superseded:** 2026-11-05

> This ADR is preserved for historical context. Auth0/OIDC integration has been removed. ILKA now manages its own credential-based authentication with preserved RBAC, organization, and site authorization.

## Context

ILKA will be multi-tenant (organization → site) and industrial. Sprint 0 left authentication **NOT DECIDED**. Custom password stacks are easy to get wrong. Operators will eventually need SSO (Entra ID, Okta, Keycloak, etc.).

## Decision

**Hybrid:**

- **Authentication** (who the human is): **OpenID Connect** against a managed or self-hosted identity provider. ILKA does **not** mint production access tokens as its primary protocol and does **not** store password hashes in the first implementation.
- **Authorization** (what they may do): ILKA database — `organizations`, `users` (linked by IdP subject + email), `roles`, `sites`, future camera/incident rows scoped by `organization_id` / `site_id`.
- **Sessions:** Use IdP-issued access/refresh tokens (short-lived access). Logout = token revocation / refresh discard at the IdP plus ILKA must treat missing/expired tokens as unauthenticated. Optional later: server-side session table for explicit revocation of refresh — **not** required in Sprint 0.5.
- **IdP product** (Keycloak vs Entra vs Auth0, etc.) remains **NOT DECIDED**. The **protocol** is OIDC.

Login APIs, password reset, and MFA UX are **not implemented** in this sprint.

## Alternatives considered

| Option | Why not primary |
| :--- | :--- |
| 1. Managed OIDC only (no local user rows) | Cannot attach org/site/role/audit without a local principal record |
| 2. Application-managed passwords (JWT in ILKA) | Custom crypto, weaker SSO path, more code to audit |
| 3. Hybrid (selected) | Local tenancy + standard identity |

## Security implications

- No fake users or shared passwords in the app.
- Camera credentials stay out of the IdP and out of logs; they are secrets referenced on camera records later.
- All mutating APIs must require an authenticated `Principal` once login exists.
- Audit log should record IdP subject / user id on authz-sensitive actions.

## Deployment

Production: configure IdP (issuer, client id, client secret in env/vault). ILKA validates JWTs from the issuer (library, not hand-rolled crypto).

## Local development

Until an IdP is chosen, `/login` remains a placeholder. Developers run API tests without authentication. Optional later: Compose Keycloak — **not** added now.

## Future SSO

Swapping IdPs is an issuer/client config change, not a rewrite of org/site RBAC.

## Why this fits ILKA

Least custom security code, matches multi-tenant industrial SSO, keeps authorization in Postgres next to sites and future cameras.
