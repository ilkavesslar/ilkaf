# Database schema

**Status:** Identity, sites, assignments, and camera **metadata** tables **IMPLEMENTED** via Alembic (`backend/alembic/`, through `0004_sites_authz_cameras`). Incidents, employees, and live video are **not** in DDL.

Primary database: **Neon PostgreSQL** (**APPROVED**, ADR 0002). Optional local Compose Postgres (ADR 0009). Do not create a production project from agents.

Migration tool: **Alembic** (**APPROVED**, ADR 0008).

## Environment model

```text
Development workstation
        ↓
Neon *development* project (not production)
        ↓
Neon branches (dev / PR / test)
        ▼
Versioned migrations (when a tool is chosen)
        ↓
Automated tests against a non-prod branch
        ↓
Production project/branch (human-only; agents have no production credentials)
```

| Actor | Permission |
| :--- | :--- |
| App (dev) | `DATABASE_URL` (canonical) or `ILKA_POSTGRES_URL` fallback — least privilege; `.env` only |
| AI inspection | `DATABASE_READONLY_URL` / Neon MCP **read-only** when configured |
| Agents | No production URLs. No autonomous DROP/TRUNCATE/DELETE/ALTER |
| Production | Human-operated; not for MCP writes |

Connection strings: `.env` only.

## Initial domain model (design, not DDL)

Avoid speculative columns (no “future JSON kitchen sink”). Types below are intent, not SQL.

### Organization — Phase 1 **yes** (single tenant row allowed)

- **Purpose:** Tenant root for multi-org later.
- **Key fields:** id, name, created_at.
- **Relationships:** 1→n Site, User memberships.
- **Security:** all operational queries scoped by organization_id.

### User — Phase 1 **yes**

- **Purpose:** Login identity for operators/engineers.
- **Key fields:** id, email (column unique, plus unique index `uq_users_email_lower` on `lower(email)`), display_name, `idp_subject` (nullable unique, OIDC subject — ADR 0010), role_id, created_at, updated_at, disabled_at. No password hash in this schema.
- **Relationships:** User → Organization; User → Role; User ↔ Site via `user_site_assignments`.
- **Security:** credentials never logged; PII; no password hash column (ADR 0010).

### Role — Phase 1 **yes** (names only)

- **Purpose:** Coarse role label until full RBAC is decided.
- **Key fields:** id, name (unique), description.
- **Relationships:** Role 1→n User.
- **Security:** coarse permission map in code; login not implemented.

### Employee — Phase 1 **no**

- **Purpose:** Plant worker record (distinct from login User).
- **Key fields:** id, site_id, display_name, employee_code, created_at.
- **Relationships:** Employee → Site.
- **Security:** HR/PII; delay until access control exists.

### Site — Phase 1 **yes**

- **Purpose:** One industrial location (tenant boundary).
- **Key fields:** id, organization_id, name, code (unique per org), description, timezone, is_active, created_at, updated_at.
- **Relationships:** Site → Organization; User ↔ Site via `user_site_assignments`; Camera → Site (metadata only).
- **Security:** all operational data scoped by site.

### UserSiteAssignment — Phase 1 **yes** (membership only)

- **Purpose:** Persist which users may operate which sites. Not a full permission matrix.
- **Key fields:** id, user_id, site_id, organization_id, optional role_id, created_at.
- **Constraints:** unique `(user_id, site_id)`; composite FKs so user, site, and assignment share `organization_id`.
- **Relationships:** User ↔ Site within one Organization.
- **Security:** cannot attach a user to another tenant's site at the database layer.

### Building — Phase 1 **no** (twin)

- **Purpose:** Site subdivision.
- **Key fields:** id, site_id, name.
- **Relationships:** Building → Site; 1→n Floor.

### Floor — Phase 1 **no**

- **Purpose:** Level within a building.
- **Key fields:** id, building_id, name.
- **Relationships:** Floor → Building; 1→n Zone.

### Zone — Phase 1 **no**

- **Purpose:** Safety/geofence area.
- **Key fields:** id, floor_id, name, polygon (geometry **NOT DECIDED**).
- **Relationships:** Zone → Floor; cameras may reference a zone.
- **Security:** zone maps are sensitive.

### Camera — Sprint 2 **yes** (metadata only; no live ingest)

- **Purpose:** Camera registry.
- **Key fields:** id, site_id, organization_id, name, code, description, location, status (`ACTIVE` / `INACTIVE` / `MAINTENANCE`), created_at, updated_at.
- **Relationships:** Camera → Site.
- **Security:** never store RTSP passwords or stream URLs on this row. Live ingest is deferred.

### Incident — Phase 1 **no**

- **Purpose:** HITL safety case (candidate vs verified **PLANNED**).
- **Key fields:** id, site_id, status, source, created_at.
- **Relationships:** Incident → Site; optional Camera; 1→n Alert.
- **Security:** operationally sensitive; CV output is not automatic confirmation.

### Alert — Phase 1 **no**

- **Purpose:** Operator-facing notification of a candidate event.
- **Key fields:** id, incident_id, severity, acknowledged_at, acknowledged_by_user_id.
- **Relationships:** Alert → Incident, User.
- **Security:** RBAC on ack/resolve when RBAC exists.

### AuditLog — Phase 1 **yes**

- **Purpose:** Who did what (auth, role change, later incident actions).
- **Key fields:** id, actor_user_id, action, entity_type, entity_id, at (UTC), metadata (non-secret).
- **Relationships:** AuditLog → User (nullable for system).
- **Security:** append-oriented; no secrets in metadata.

No detections/model-registry tables in this first model.
