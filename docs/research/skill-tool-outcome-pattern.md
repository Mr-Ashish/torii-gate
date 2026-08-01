# F114 research note — Tool-invocation skill outcome scoring

**Date:** 2026-08-01  
**Fire:** F114

## Sources

1. **Mem2ActBench / proactive memory:** memory tools only help if the agent *calls* them; inject presence ≠ utilization.
2. **Vercel agent evals:** skills often never invoked when dumped wholesale — measure invocation.
3. **Torii F105/F106:** memory-tool-audit scores utilization; F113 adopted `skill-prefer-memory-cli-early` teaching `torii.py memory`.
4. **Gap:** F84 `score_hits` only scanned **review prose keywords** — recovery skills fire via **terminal**, not review body tokens. Also F105 missed F110 product CLI (`torii.py memory`).

## Pattern

| Layer | Role |
|-------|------|
| Maker | Hermes follows skill → calls memory CLI mid-review |
| F105 audit | Detect `torii_memory.py` **and** `torii.py memory` |
| F114 score | `prose_hit` OR `tool_hit` → combined `hit` for fitness |
| Router | `skill-prefer-memory-cli-early` always-on full body |
| Fitness | ingest tool_hit_n; avoid zombie-demote of tool-only skills |

## TOOL_OUTCOME_PROBES (excerpt)

- `skill-prefer-memory-cli-early` → `torii.py memory`, `torii_memory.py`, archival/graph scripts
- `skill-tool-depth-hunks` → `rg -n`, `sed -n`, diff
- Optional probes for chain/taint skills

## Success metric

- Offline: fixture tool_outcome_ok; product CLI in good_tools; weak silent prose + empty tools = miss
- Live: skill-hits.json has f114 + tool_outcome; always skill in prompt; Modal BIT3_OK
