# F147 research note — Recon-warm → core tier promote

**Date:** 2026-08-01  
**Fire:** F147

## Sources

1. MemGPT/Letta: core = always-in-context; archival = cold until paged.
2. F146 reconsolidation stamps `last_retrieved_at` on successful promote.
3. Without tier promotion, warm store fields never enter core inject budget.

## Gap

F146 warms durable TP rows but F97 classify only used path_match / effective_score. Recently retrieved cold themes stayed archival until path hit — reconsolidation did not compound into the OS hierarchy.

## Pattern

| Layer | Role |
|-------|------|
| `recon_warm_meta` | windowed last_retrieved / recon flag |
| `classify_item` | warm → core (skip superseded) |
| scoped_memory_recall | pass recon fields on TP load |
| env | `TORII_MEMORY_RECON_CORE=1`, hours=168 |

## Success

- Fixture f147_ok: pickle-recon core; old-recon/dead-recon archival; cold without F147
- Metric core_recon_warm ≥ 1
