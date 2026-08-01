# F130 research note — Memory util-eval → product scorecard

**Date:** 2026-08-01  
**Fire:** F130

## Sources

1. **Mem0 / Letta 2026:** memory layers only improve outcomes when agents **call** memory tools (not passive inject).
2. **IFCMemoryBench / WorldMemArena:** decompose ingestion · retrieval · **utilization**.
3. F105/F106: local audit + re-prompt existed; product scorecard (F129) only demoted critic metrics.
4. Loop-eng: score the loop — memory util belongs next to demote_rate on the front door.

## Pattern

| Layer | Role |
|-------|------|
| memory_tool_audit util-eval | offline good vs inject-unused weak |
| paper metric | memory_tool_util_delta |
| product scorecard | brand_ready requires util eval_pass |
| brand md | table row for util delta |

## Success

- util-eval delta ≥ 0.4 eval_pass
- scorecard brand_ready includes memory_util_eval_pass
