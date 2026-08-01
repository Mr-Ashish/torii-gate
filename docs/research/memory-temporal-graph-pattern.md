# F100 research note — Zep-style temporal memory edges

**Date:** 2026-08-01  
**Fire:** F100  
**Memory OSS:** Zep temporal KG patterns only (no vendored runtime)

## Sources

1. Zep: facts as graph edges with temporal validity (valid_at / invalid_at).
2. Torii F93: `superseded_by` on DELETE — not queryable as graph.
3. F98/F97 search/tiers still flat bags of items.

## Pattern

| Zep idea | Torii F100 |
|----------|------------|
| Temporal edge | `valid_from` / `valid_until` on edges |
| Supersession | `supersedes` from F93 fields |
| Entity relations | `same_theme`, `co_path` |
| Query | 1-hop neighbors by path/theme/id |

## Wire

- `memory_temporal_graph.py` build/query/inject/fixture
- assemble-context soft inject; post-review rebuild
- memory_loop stage `temporal_graph`

## Success

- fixture: supersede + theme + co_path + temporal_ok
- memory_loop L3
