# F96 research note — Memory compound loop readiness + promoted inject rank

**Date:** 2026-08-01  
**Fire:** F96

## Sources

1. Loop Engineering readiness scorecards L0–L3 (skill_loop F91 pattern).
2. Torii F75–F95 memory stack: write events, consolidate, effective critic, federate.
3. Gap: promoted `effective_score` themes not preferred in F75 inject; no ops “is memory ready?” surface.

## Pattern

| Piece | Torii F96 |
|-------|-----------|
| Prefer promoted signals | `_fed_path` loads `promoted-signals.json` first |
| Rank by effective | theme-only + federated high-eff boost in `rank_score` |
| Max-merge strength | `merge_items` keeps max `effective_score` |
| Readiness scorecard | `memory_loop_status` stages write→…→scoped_recall |
| Smoke / gate | smoke [7/7]; `--memory-loop-only` |

## Success

- scoped fixture: promoted_ok + effective_rank_ok
- memory_loop fixture L3
- smoke PASS with both skill + memory loops
