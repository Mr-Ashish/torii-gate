# F97 research note — Letta-style core / archival memory tiers

**Date:** 2026-08-01  
**Fire:** F97  
**Memory OSS:** Letta/MemGPT hierarchy (patterns only)

## Sources

1. MemGPT/Letta: core (RAM, always in context) vs archival (cold) vs recall (paged history).
2. Torii F75 flat top-N inject; F94/F96 effective scores measure hotness but did not gate tier.
3. F92 skill-loop CI job summary — mirror for memory_loop.

## Pattern

| Letta idea | Torii F97 |
|------------|-----------|
| Core always-in-context | path-matched OR effective ≥ floor OR path-FP |
| Archival cold | low-effective theme noise; sparse inject |
| Budget | CORE_MAX / ARCHIVAL_MAX env knobs |
| Self-edit tools | deterministic tools-as-code (no LLM paging yet) |

## Wire

- `memory_tiers.py` classify / inject / fixture
- `scoped_memory_recall.recall` → `apply_to_recall_result`
- render embeds core/archival sections
- CI job summary + optional `torii/memory-loop` status
- memory_loop_status stage `tiers`

## Success

- fixture: path + hot-eff in core; high-hit low-eff in archival
- memory_loop still L3; smoke PASS
