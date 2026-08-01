# F142 research note — Memory util hub post-score compound

**Date:** 2026-08-01  
**Fire:** F142

## Sources

1. F125/F138 hub post-score: federated util → skill priority deltas.
2. Mem0 multi-tenant namespaces: share util themes not raw memory.
3. F141 federate without post-score left priority inert.
4. MIA compound memory: quality+frequency rewards for next retrieval strategy.

## Pattern

| Layer | Role |
|-------|------|
| memory-util-signals.json | F141 multi-tenant util bins |
| post_score_memory_util_hub | skill_id → priority_delta (cap +40) |
| select_skills | always/score bump for memory-cli |
| inject | `<!-- torii-f142-memory-util-hub -->` |
| CLI | hub-score |

## Env

- `TORII_MEMORY_UTIL_HUB=1` (default)

## Success

- Fixture f142_ok: skill_n≥1, delta≥5, inject marker, privacy_ok
