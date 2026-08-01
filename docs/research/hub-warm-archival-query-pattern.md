# F149 research note — Hub recon-warm → archival auto-query

**Date:** 2026-08-01  
**Fire:** F149

## Sources

1. F148 recon-warm-signals + post_score_recon_warm_hub (write-only without query bias).
2. F144 multi-hop themes expand auto-query (local graph only).
3. Mem0 multi-tenant: shared themes must change next retrieval, not only dashboards.

## Gap

Hub warm themes were scored but never folded into MemGPT archival auto-query. Cross-tenant retrieval heat stayed inert for paging cold TPs.

## Pattern

| Layer | Role |
|-------|------|
| post_score_recon_warm_hub | privacy themes + priority |
| auto_from_paths | hub themes → query tokens |
| apply_hub_theme_boost | soft score boost on match |
| env | TORII_RECON_WARM_HUB_QUERY=1 |

## Success

- Fixture f149_ok: hub theme insecure_deserialization in query; pickle hub_boost
- mode auto_hub; section F149
