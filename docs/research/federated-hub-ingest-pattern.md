# F77 research note — cross-tenant hub federated ingest

**Date:** 2026-08-01  
**Fire:** F77

## Sources

1. IETF draft *Privacy-Preserving Federated Learning for Multi-Tenant Agent Systems* (2026) — aggregate without raw tenant data.
2. Multi-tenant RAG isolation failures — relevance retrieval can leak cross-tenant secrets; never share paths/snippets.
3. Torii F65 tenant layout + F71 local `federate()` + F75 scoped recall — hub merge was missing.

## Pattern

| Idea | Port |
|------|------|
| Secure aggregation mindset | theme/CWE/keywords only; `tenant_hash` not raw id |
| Unique client counting | `tenant_hashes[]` → `tenants` |
| Poison filter | strip `/Users/`, secrets, snippets; promote `min_tenants≥2` |
| Hub layout | `memory/federation/` + per-tenant `memory/tenants/{t}/federation/` |

## Success metric

- Two-tenant fixture: `sql_injection.tenants≥2`, privacy_file_ok, promote excludes single-tenant noise
- hub-ingest payload with `federated_signals` writes FEDERATED_HUB
