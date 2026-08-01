# F148 research note — Recon-warm theme federate + hub post-score

**Date:** 2026-08-01  
**Fire:** F148

## Sources

1. Mem0 multi-tenant: share util/theme signals not raw memory.
2. F141/F142 memory util federate + hub post-score.
3. F146/F147 reconsolidation warms local store/tier only — multi-tenant heat was silent.

## Gap

Successful archival retrieve compounds locally (hits, core tier) but other tenants never learn which themes are retrieval-hot. Federation of full ids/paths would leak; need theme-only warm signals.

## Pattern

| Layer | Role |
|-------|------|
| federate_recon_warm | themes + warm_bin + tenant_hash |
| recon-warm-signals.json | privacy-safe store |
| post_score_recon_warm_hub | priority themes for next inject |
| env | TORII_RECON_WARM_FEDERATE=1 |

## Success

- Fixture f148_ok: sql_injection theme signal; no tenant string; no /Users/
- Section lists F148; hub privacy_ok
