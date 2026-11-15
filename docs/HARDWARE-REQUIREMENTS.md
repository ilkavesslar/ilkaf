# Hardware requirements

**Status:** **PLANNED**. No vendors or SKUs **APPROVED**. Do not buy hardware from this file alone.

## Layers

| Layer | Role | Notes |
| :--- | :--- | :--- |
| Camera | PoE IP, preferably ONVIF S | Not laptop webcams in production |
| Network | Managed PoE switch | VLAN/QoS later |
| Edge | CPU; GPU if inference at edge | Sizing after camera count is known |
| Application | Host for ILKA API/UI | Same box as edge for small sites |
| Database | PostgreSQL (Neon or equivalent) | Managed is fine for non-air-gapped |
| Event | None in Phase 1; later optional bus | See EVENT-ARCHITECTURE.md |
| User | Browser workstation | Operator console |

## Sizing (guidance only, not a purchase list)

- **Minimum (lab):** 1–2 cameras, CPU inference, one PC, Neon free/dev.
- **Recommended (pilot):** dedicated PoE switch, 4–8 cameras, discrete GPU if FPS/latency miss CPU, UPS.
- **Scalable:** more edge nodes per hall; do not assume one GPU serves unlimited streams.

Camera count per node is **NOT DECIDED** (open question in requirements). Measure before scaling.
