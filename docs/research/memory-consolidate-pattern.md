# F94 research note — Memory consolidation (importance · merge · decay · eviction)

**Date:** 2026-08-01  
**Fire:** F94  
**Memory OSS:** oss-memory-mem0 (Apache-2.0 patterns) + public consolidation surveys — no vendored runtime

## Sources

1. Hindsight/Vectorize (2026): four-lever consolidation — importance, merge, decay, eviction.
2. Mem0 ECAI 2025 / state-of-memory 2026: write-time ADD/UPDATE/DELETE + consolidation; staleness of high-hit facts is the hard open problem.
3. Zep: temporal graph edge strength / age as first-class retrieval signal.
4. Torii F93 event policy (writes); F75 scoped recall (path/scope/hits) — no temporal maintenance.

## Pattern ported

| Lever | Torii F94 |
|-------|-----------|
| importance | hits + path specificity + keywords + CWE → `importance_score` |
| merge | same theme + Jaccard keywords ≥ threshold → MERGE into keeper |
| decay | exponential half-life (`TORII_MEMORY_HALF_LIFE_DAYS`, default 30d) |
| eviction | `effective = importance × decay` below threshold → EVICT |

## Wire

- `merge_tp_signatures` soft-calls `consolidate_items` when `TORII_MEMORY_CONSOLIDATE=1`
- `run-torii-review.sh` stage `memory_consolidate run --kind both`
- F75 `rank_score` blends `effective_score` when annotated
- Toggle `TORII_MEMORY_CONSOLIDATE` (default on)

## Success

- fixture: merge near-dup sqli, decay-rank fresh cmdi > stale xss, evict ancient noise
- bench fixture still pass; pytest green
