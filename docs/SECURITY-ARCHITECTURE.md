# Security architecture

**Status:** Architecture **APPROVED** (ADR 0011). Sprint 2 **IMPLEMENTED** token validation and ILKA authorization. Auth0/OIDC has been removed; custom ILKA-managed authentication is **SCAFFOLDED**. Canonical notes: `docs/authentication.md`, `docs/authorization.md`. Root `SECURITY.md` is the long-term baseline; §2.1 follows ADR 0011.

ILKA handles employee, camera, incident, and video data. Treat it as sensitive industrial OT-adjacent software.

## Requirements (design)

- **Authentication:** ILKA-managed email/password with Argon2id password hashes and signed sessions (ADR 0011). Full credential authentication is **not yet implemented**; the skeleton fails closed with 401.
- **Authorization / RBAC:** ILKA owns org/site/role records. Helpers in `backend/app/core/rbac.py`. Protected routes return **401** until a principal exists. Candidate roles: SYSTEM_ADMIN, ORG_ADMIN, SITE_MANAGER, SAFETY_OFFICER, OPERATOR, VIEWER.
- **Tenant isolation:** `organization_id` on operational data. Users other than `SYSTEM_ADMIN` receive **404** (same as missing) for foreign-organization sites and cameras. Permission failures on visible resources remain **403**.
- **Secrets:** env/vault only. Never git. Never logs. Camera/RTSP passwords in a secret reference, not camera rows in plaintext if avoidable.
- **API:** TLS off-localhost, validation, rate-limit login, parameterized queries, CORS allowlist.
- **Cameras:** segmented network **PLANNED**; signed/expiring view URLs **PLANNED**; export audited.
- **Service-to-service:** none in Phase 1 (single process). Later: mTLS or equivalent **NOT DECIDED**.
- **Audit:** auth, config, incident transitions, stream export.
- **Dependencies:** lockfiles + scanning when packages exist.
- **Least privilege:** Neon app role vs read-only inspection; agents never get production URLs.

## Explicit non-goals until decided

PLC/physical sirens (N9). Automated punitive HR actions without HITL (A5).
