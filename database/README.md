# Database Management (PostgreSQL)

## Responsibilities
- Production-grade schema definitions, constraints, indices, and relationships.
- Managed, reversible database migrations (e.g., Alembic).
- Baseline seed data (default roles, permissions, incident types, mock plant layouts).

## Directory Layout (Planned)
```text
database/
├── migrations/             # Migration versions
├── schemas/                # Raw SQL/DDL schema definitions and ERDs
└── seeds/                  # Seed scripts for initial roles, incident definitions
```
