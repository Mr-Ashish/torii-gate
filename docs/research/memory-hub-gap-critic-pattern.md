# F143 research note — Memory util hub gap critic

**Date:** 2026-08-01  
**Fire:** F143

## Sources

1. F127/F139 hub gap critic: multi-tenant gap_pressure + local idle → demote APPROVE.
2. F141/F142 memory util federate + hub post-score without panel demote on hub gap.
3. Mem0/Letta multi-tenant: under-use of memory tools is systemic risk signal.

## Pattern

| Layer | Role |
|-------|------|
| post_score_memory_util_hub | gap_pressure from federated util bins |
| memory-tool-audit.json | local inject + hit_count |
| f143_memory_hub_gap | checker weight 0.07 |
| decide_verdict | APPROVE → COMMENT on high+idle |

## Env

- `TORII_MEMORY_HUB_GAP_CRITIC=1` (default)
- `TORII_MEMORY_HUB_GAP_THR=0.34` (default)

## Success

- Fixture f143_ok; demote APPROVE when hub gap + local idle
