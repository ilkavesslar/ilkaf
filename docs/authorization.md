# Authorization (roles, permissions, site scope)

**Status:** **IMPLEMENTED** for Sprint 2 site and camera-metadata APIs. Safety events and live video are **not** authorized here because they are not implemented.

Authentication (`docs/authentication.md`) answers *who*. This document answers *what they may do*.

```text
             OIDC
              ↓
           Identity
              ↓
          Active User
              ↓
       Role + Permission
              ↓
          Site Scope
              ↓
       Protected ILKA API
```

## Roles

Canonical names live in `backend/app/core/rbac.py` (`RoleName`). Database rows are seeded in migration `0004_sites_authz_cameras`.

| Role | Sprint 2 meaning |
| :--- | :--- |
| `SYSTEM_ADMIN` | Cross-tenant administration. This is ILKA’s **ADMIN** capability. |
| `ORG_ADMIN` | All sites in the user’s organization |
| `SITE_MANAGER` | Manage assigned site resources |
| `SAFETY_OFFICER` | Safety-related access on assigned sites |
| `OPERATOR` | Operational monitoring on assigned sites |
| `VIEWER` | Read-only on assigned sites |

A user has a **global** role (`users.role_id`). `user_site_assignments.role_id` may override the effective role at a specific site.

## Permission matrix

Permissions are centralized in `PERMISSIONS`. Legacy names such as `site.read` map onto these values.

| Permission | SYSTEM_ADMIN | ORG_ADMIN | SITE_MANAGER | SAFETY_OFFICER | OPERATOR | VIEWER |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `sites:read` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `sites:create` | ✓ | ✓ | | | | |
| `sites:update` | ✓ | ✓ | ✓ (assigned) | | | |
| `sites:delete` | ✓ | ✓ | | | | |
| `users:read` | ✓ | ✓ | ✓ | | | |
| `users:manage` | ✓ | ✓ | | | | |
| `cameras:read` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `cameras:create` | ✓ | ✓ | ✓ | | | |
| `cameras:update` | ✓ | ✓ | ✓ | | | |
| `cameras:delete` | ✓ | ✓ | ✓ | | | |
| `safety:read` | ✓ | ✓ | ✓ | ✓ | ✓ | |
| `safety:manage` | ✓ | ✓ | | ✓ | | |

`SYSTEM_ADMIN` is stored as `*`. Site-scoped roles still cannot access sites they are not assigned to, except `SYSTEM_ADMIN` / `ORG_ADMIN`.

## Site assignments

```text
User ── user_site_assignments ── Site
                 │
              optional role
```

`GET /api/sites` filters at the query layer:

- `SYSTEM_ADMIN`: all sites
- `ORG_ADMIN`: sites in the user’s organization
- others: assigned `site_id`s only

## Site-scoped flow

```text
Authenticate user
      ↓
Determine requested site
      ↓
Check assignment (or org-wide role)
      ↓
Check permission (effective role at that site)
      ↓
Allow or deny
```

## HTTP status

| Situation | Status |
| :--- | :--- |
| Missing/invalid/expired token, or unprovisioned identity | **401** |
| Authenticated but inactive | **403** |
| Authenticated without permission on a resource the user is allowed to know exists | **403** |
| Site-scoped user asking for another site (or unknown id) | **404** (does not leak whether the site exists) |
| Non-`SYSTEM_ADMIN` asking for a **foreign-organization** site or camera | **404**, same body as a missing resource |
| `SYSTEM_ADMIN` asking for a missing site/camera | **404** |
| Duplicate site/camera code | **409** |

There is no `DELETE /api/sites` in Sprint 2.

## Camera registry

Camera APIs store **metadata only** (name, code, location, status). Live camera/RTSP functionality is intentionally deferred. Camera rows are always scoped by `site_id` + `organization_id`.
