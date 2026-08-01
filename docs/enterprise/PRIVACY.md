# Federation privacy one-pager

**Buyer line:** *Torii can compound learning across orgs without sharing code, paths, or raw tenant IDs.*

## What leaves a tenant (when hub federation is enabled)

| Allowed field | Example | Why |
|---------------|---------|-----|
| **theme** | `sql_injection` | Pattern class only |
| **CWE** | `CWE-89` | Standard taxonomy |
| **keywords** | `parameterized`, `f-string` | Short tokens for routing |
| **path basenames** | `app.py` | Filename only — not full path |
| **tenant hash** | `e28384f7c5c5` | SHA-256 prefix — not org name |
| **hits / bins** | util bins, warm bins | Aggregate counters |

## What never leaves a tenant

| Forbidden | Why |
|-----------|-----|
| Full filesystem paths (`/Users/…`, `/home/…`) | Identity + layout leak |
| Source snippets / diffs | Code exfil |
| Secrets, API keys, tokens | Credential leak |
| Raw tenant / org / repo names in global aggregates | Re-identification |
| Signature blob bodies / evidence quotes | Content leak |
| PR titles / author emails | PII |

## How we enforce it

1. **Sanitize on write** — `federated_hub_ingest.sanitize_signal` strips to the allowlist and rejects poison.  
2. **`privacy_ok` flag** — each federation file records a privacy scan; product surface fails closed if `privacy_ok` is false.  
3. **Audit CLI** — `python3 scripts/enterprise_surface.py fixture` scans `memory/federation/*.json` for home paths and raw tenant strings.  
4. **Promote gate** — themes need **≥ min_tenants** (default 2) before multi-tenant inject boost.

## Operator checklist

```bash
# Privacy posture
python3 scripts/enterprise_surface.py status

# Offline audit (CI-friendly)
python3 scripts/enterprise_surface.py fixture

# Engine fixture (two synthetic tenants)
python3 scripts/federated_hub_ingest.py fixture
```

## Defaults

| Setting | Default | Notes |
|---------|---------|-------|
| Repo-local `.torii/` | **on** | No hub required |
| Hub federation | opt-in / hub-side | Themes only when enabled |
| `TORII_FED_MIN_TENANTS` | **2** | Single-tenant cannot promote alone |
| Modal webhook open | **off** | See ops reliability |

## Related

- Org isolation story: [ORG-ISOLATION.md](ORG-ISOLATION.md)  
- Ops fail-closed: [`docs/ops/RELIABILITY.md`](../ops/RELIABILITY.md)  
- Engine: `scripts/federated_hub_ingest.py` (F77+)
