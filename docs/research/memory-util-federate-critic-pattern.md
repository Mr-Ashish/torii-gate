# F141 research note — Memory util federate + critic demote

**Date:** 2026-08-01  
**Fire:** F141

## Sources

1. Mem0/Letta: memory only helps if tools are called mid-run.
2. F105/F106 audit + re-prompt without multi-tenant federate or panel demote.
3. F121/F136 skill util: inject ≠ use → federate themes + demote APPROVE.
4. IFCMemoryBench: utilization is a first-class memory quality axis.

## Pattern

| Layer | Role |
|-------|------|
| memory-tool-audit.json | F105 score + utilization_gap |
| federate_memory_util | memory-util-signals.json (bins + tool ids) |
| f141_memory_util | critic weight 0.07 |
| decide_verdict | APPROVE → COMMENT on inject_unused |

## Env

- `TORII_MEMORY_UTIL_FEDERATE=1` (default)
- `TORII_MEMORY_UTIL_CRITIC=1` (default)

## Success

- Fixture f141_ok privacy; critic demotes gap APPROVE
- No `/Users/` or raw tenant strings
