# F102 research note — Multi-hop co_path → supersede demote

**Date:** 2026-08-01  
**Fire:** F102

## Sources

1. Zep multi-hop retrieval over temporal edges.
2. F100/F101: 1-hop supersedes only; path kinship unused by critic.
3. AppSec reality: FP resolve on `app.py` should caution same theme on co-path siblings.

## Pattern

| Step | Torii F102 |
|------|------------|
| Seed | nodes matching finding paths |
| Expand | BFS co_path + same_theme (hops default 2) |
| Collect | supersedes in/near neighborhood + inactive seed themes |
| Critic | dual_pass re-indexes per chunk with paths |

## Env

- `TORII_GRAPH_MULTI_HOP=1` (default)
- `TORII_GRAPH_HOPS=2`

## Success

- fixture multi_hop_ok; dual_pass path-local demote
