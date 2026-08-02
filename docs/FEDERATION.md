# Torii Gate — privacy-safe federation

**Buyer story:** *Cross-tenant learning compounds the gate — without sharing code, paths, or org names.*

```text
tenant A review ──► themes / CWE / basenames + tenant hash ──► hub
tenant B review ──► same allowlist only                  ──► hub
                              │
                              ▼
              multi-tenant heat → quieter next PR (still path-evidenced)
```

## JTBD (merge authority)

| Buyer | Win |
|-------|-----|
| **AppSec** | Shared attack *themes* raise always-priority skills without raw findings dumps |
| **Platform** | Hub learning opt-in; default is still **repo-local** `.torii/` |
| **Compliance** | Allowlist fields only; home paths / snippets / secrets never leave the tenant |

Federation does **not** replace the required check **`torii/gate`**. It makes the next run **stricter and quieter** when multi-tenant heat agrees.

**Day-2 one screen:** `python3 scripts/torii.py status --text` shows buyer security heat on the **merge** beat (`fed heat=sql_injection,… (mt=N)`) — util/skill research themes are filtered so AppSec sees attack themes, not ops noise.

## What is shared (allowlist)

| Field | Example |
|-------|---------|
| theme / CWE | `sql_injection` · `CWE-89` |
| keywords | short routing tokens |
| basenames | `app.py` (not full paths) |
| tenant hash | SHA-256 prefix — not org name |
| aggregate bins | util / warm counters |

Full allow/deny table: [`enterprise/PRIVACY.md`](enterprise/PRIVACY.md).

## What never leaves a tenant

Full paths · source snippets · secrets · raw org/repo names · PR authors · evidence quotes · **cost/PR USD estimates · hermes token counts · Modal run URLs**.

Measured dogfood cost/latency lives in the **local hub vault** (`docs/benchmarks/traces/`, [ops/cost-pr-dashboard.md](ops/cost-pr-dashboard.md)) — themes federation never carries spend data. See [enterprise/PRIVACY.md](enterprise/PRIVACY.md) · Cost / PR telemetry.

## Operator path

```bash
# Day-2 one screen — Org beat: isolation · fed themes-only · mt_themes
python3 scripts/torii.py status --text

# Privacy + isolation product surface
python3 scripts/torii.py enterprise -- status
python3 scripts/torii.py enterprise -- fixture

# Hub engine (privacy-safe collect / promote)
python3 scripts/torii.py federation -- status
python3 scripts/torii.py federation -- fixture

# Report inventory
python3 scripts/enterprise_surface.py report
```

| Default | Value |
|---------|--------|
| Repo-local memory | **on** (no hub required) |
| Hub federation | **opt-in** |
| Promote min tenants | **2** (single tenant cannot promote alone) |
| Cost / PR telemetry | **local vault only** (never federated) |

## How it ties to quieter + tools

- Multi-tenant recovery / hub-archival heat can raise always-on recovery skills.  
- Still require **path:line** evidence and tool use — federation is routing heat, not auto-block.  
- Measure: [`QUIETER.md`](QUIETER.md) · [`TOOL-USE.md`](TOOL-USE.md) · [`WORKFLOWS.md`](WORKFLOWS.md).

## Related

- Org isolation diagram: [`enterprise/ORG-ISOLATION.md`](enterprise/ORG-ISOLATION.md)  
- Enterprise surface: [`enterprise/README.md`](enterprise/README.md)  
- Engine: `scripts/federated_hub_ingest.py`  
- Gate contract: [`GATE.md`](GATE.md)
