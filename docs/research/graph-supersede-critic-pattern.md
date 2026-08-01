# F101 research note — Graph supersede demote in dual-pass critic

**Date:** 2026-08-01  
**Fire:** F101

## Sources

1. F100 temporal `supersedes` edges (Zep validity + F93 DELETE).
2. F70/F95 dual_pass: path + effective floor — no graph awareness.
3. Loop-eng maker/checker: checker must recompute offline signals.

## Pattern

| Signal | Critic action |
|--------|----------------|
| Active supersedes edge target id | status=`superseded_tp` (not confirmed_tp) |
| Superseded theme in finding text | demote even if TP sig deleted from active store |
| TORII_GRAPH_SUPERSEDE=0 | legacy dual_pass only |

## Wire

- `memory_temporal_graph.superseded_index` / `load_or_build_graph`
- `bench_security_gate.dual_pass_critic` loads graph soft
- F78 panel surfaces `superseded_tp` counts

## Success

- fixture: sqli superseded demoted; cmdi still confirmed
- toggle off → no superseded_tp
