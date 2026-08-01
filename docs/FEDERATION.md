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

Full paths · source snippets · secrets · raw org/repo names · PR authors · evidence quotes.

## Operator path

```bash
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

## How it ties to quieter + tools

- Multi-tenant recovery / hub-archival heat can raise always-on recovery skills.  
- Still require **path:line** evidence and tool use — federation is routing heat, not auto-block.  
- Measure: [`QUIETER.md`](QUIETER.md) · [`TOOL-USE.md`](TOOL-USE.md) · [`WORKFLOWS.md`](WORKFLOWS.md).

## Related

- Org isolation diagram: [`enterprise/ORG-ISOLATION.md`](enterprise/ORG-ISOLATION.md)  
- Enterprise surface: [`enterprise/README.md`](enterprise/README.md)  
- Engine: `scripts/federated_hub_ingest.py`  
- Gate contract: [`GATE.md`](GATE.md)
