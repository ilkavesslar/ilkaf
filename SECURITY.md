# Security Architecture & Policies (SECURITY.md)

> [!IMPORTANT]
> **Baseline Status Notice**: This document is the **long-term security baseline** for ILKA. It is **not** a description of implemented authentication. **Phase 1 identity architecture is ADR 0010** (`docs/DECISIONS/0010-hybrid-oidc-authorization.md`). Engineering notes: `docs/SECURITY-ARCHITECTURE.md`. Prior to production rollout in real-world industrial facilities, this baseline must undergo formal third-party penetration testing, compliance certification (e.g., ISO/IEC 27001, SOC 2 Type II), and expansion into an operational Security Operations Manual.

---

## 1. Core Security Principles

1. **Defense in Depth**: Layered security controls spanning network isolation, application identity, service authentication, database access controls, and media stream encryption.
2. **Zero Trust & Least Privilege**: Every service, worker, and human user is granted only the minimum permissions required to perform their explicit function.
3. **Safety & Security Convergence**: Security controls must enhance, rather than compromise, real-time safety alerting.

---

## 2. Security Domains & Baseline Specifications

### 2.1 Authentication (ADR 0010 is canonical)

**Implemented today:** OIDC bearer validation (JWKS / RS256), provisioned users, RBAC, site scope. No password store. No application-minted production JWTs. Unsigned or missing tokens return **401**. Identity headers other than a verified Bearer token are not trusted.

**Production identity (approved architecture):**

- **Authentication** uses **OpenID Connect** against a managed or self-hosted identity provider. The IdP product is **NOT DECIDED**.
- ILKA **does not** store password hashes in the first implementation.
- ILKA **does not** mint production access tokens as its primary protocol. Access/refresh tokens are **IdP-issued**. ILKA will validate IdP JWTs (library, not hand-rolled crypto) when login is implemented.
- Local `User` rows link `idp_subject` + email to organization, role, and site membership.

**Obsolete for Phase 1 (do not implement):** application-managed password hashing (Argon2id/bcrypt) and ILKA-issued JWT/PASETO stacks as the production login protocol. Those ideas conflict with ADR 0010. Changing this requires a new accepted ADR.

**Target-state (post-Phase-1 / IdP capabilities, not ILKA custom crypto):** MFA for administrative and safety-supervisor roles should be enforced **at the IdP**. Optional later: server-side session table for refresh revocation.

OIDC issuer, client id, and client secret belong in environment/vault only. A browser login/redirect UI is **not** implemented in Sprint 2.

### 2.2 Authorization & Role-Based Access Control (RBAC)

- Strict RBAC enforced at the API, service, and database query levels **once a validated `Principal` exists**.
- Authorization records live in PostgreSQL (organizations, users, roles, sites, `user_site_assignments`).
- Baseline roles (names; login not implemented):
  - **SYSTEM_ADMIN**, **ORG_ADMIN**, **SITE_MANAGER**, **SAFETY_OFFICER**, **OPERATOR**, **VIEWER**
- Mapping to operator titles (Plant Operator, Safety Officer, System Administrator, Compliance Auditor) is a **product overlay**, not a second auth stack.

### 2.3 Secrets & Credential Management
- No plaintext credentials, private keys, or API tokens committed to source code or stored in unencrypted configurations.
- Dynamic environment variable injection via dedicated secret managers (e.g., HashiCorp Vault, AWS Secrets Manager, or Kubernetes Secrets).
- `DATABASE_URL` is canonical for production. `ILKA_POSTGRES_URL` is a development/CI fallback. Never commit `.env`.

### 2.4 API & Network Security
- Mandatory TLS 1.3 encryption for all external and inter-service HTTP, WebSocket (WSS), and gRPC traffic **in production**.
- Strict rate-limiting, IP whitelisting for camera ingestion interfaces, and CORS policies (**PLANNED** beyond current localhost CORS allowlist).

### 2.5 Input Validation & Sanitization
- Strict schema validation for all ingress payloads using typed schemas (Pydantic / Zod).
- Protection against SQL injection (enforced through parameterized queries / ORM), Cross-Site Scripting (XSS), and Cross-Site Request Forgery (CSRF).

### 2.6 Camera & Video Stream Security
- **PLANNED.** Secure RTSP (RTSPS) or SRTP/WebRTC encapsulation for industrial camera feeds.
- Network segmentation: Industrial camera VLANs isolated from public internet and standard corporate subnets.
- Ephemeral, signed streaming URLs for frontend video viewing with time-bounded tokens.

### 2.7 Worker Privacy & Data Protection (PII)
- **PLANNED.** Automated face and license-plate redaction/blurring pipelines where mandated by regional privacy regulations (e.g., GDPR, CCPA).
- Video snapshot and event storage encryption at rest (AES-256).

### 2.8 Audit Logging & Non-Repudiation
- Tamper-evident, structured JSON audit logs capturing:
  - User authentication and authorization attempts.
  - Safety incident generation, status transitions, and operator acknowledgements.
  - Safety threshold and zone boundary configuration changes.
  - Video stream access and export events.
- Foundation table `audit_logs` exists; login events are **not** written yet.

### 2.9 Dependency Security & Supply Chain
- Continuous vulnerability scanning of third-party dependencies (e.g., Dependabot, Snyk, `pip-audit`, `npm audit`).
- Pinned dependency versions and cryptographic lockfiles (`poetry.lock` / `package-lock.json`).

### 2.10 Incident Response & Safe Failure
- **Target-state / post-Phase-1.** Automated alerting on anomalous security events (e.g., brute force attempts, camera disconnect bursts).
- Documented incident response playbook for security breaches.
- Physical fail-safe sirens/alarms are **out of scope** for the Phase 1 modular monolith (see requirements N9).

### 2.11 Backup & Disaster Recovery
- **Target-state / post-Phase-1.** Automated, encrypted daily database backups with point-in-time recovery (PITR) testing.
- Documented Recovery Time Objective (RTO < 1 hour) and Recovery Point Objective (RPO < 5 minutes) for core safety metadata.

---

## 3. Vulnerability Disclosure & Reporting

If you discover a security vulnerability, please submit a detailed confidential report to:
`security@ilka-safety.local` (or designated internal security contact).

Include:
- Vulnerability description and CVSS estimation.
- Step-by-step reproduction instructions.
- Potential impact on industrial plant safety or data confidentiality.
