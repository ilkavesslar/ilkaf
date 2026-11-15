# ILKA — project overview

**ILKA** is an industrial safety monitoring platform for plants, warehouses, and similar sites. It is **not** a webcam demo: production cameras are expected to be PoE IP cameras on a managed network, with optional edge inference.

**Status:** repository is **SCAFFOLDED** (folders, agent rules, architecture docs). No application runtime is **IMPLEMENTED**.

## What ILKA is for

Help operators see **candidate** safety issues (PPE, zones, unsafe behavior, person-down, proximity) with enough context to verify them, record incidents, and leave an audit trail.

Software **cannot** guarantee physical safety by itself. ILKA is a monitoring and workflow aid. Camera or model failure must be visible as degraded monitoring, not a silent “all clear.”

## How it will be built

Incremental modular monolith: React + TypeScript UI → Python API → Neon PostgreSQL. Computer vision and camera ingestion are **modules** (`cv/`, `ai/`), not separate production services, until scale or isolation requires extraction (`docs/DECISIONS.md` A8).

Cursor implements; Codex reviews; Claude reviews architecture/CV/UX when useful; humans approve architecture, security, and merges to `main`.

## Read next

1. [SYSTEM-ARCHITECTURE.md](./SYSTEM-ARCHITECTURE.md)
2. [ROADMAP.md](./ROADMAP.md)
3. [DECISIONS.md](./DECISIONS.md)
