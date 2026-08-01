# F145 research note — Supersede-aware archival promote

**Date:** 2026-08-01  
**Fire:** F145

## Sources

1. MemoTime (arXiv 2510.13614): temporal faithfulness in multi-hop TKG reasoning.
2. Zep/F100–F102: `supersedes` edges with `valid_from` / `valid_until` + multi-hop path kinship.
3. F144: multi-hop themes expand archival auto-query → promote without temporal filter.

## Gap

F144 pages cold co_path themes into core. Without a supersede gate, resolved FPs / inactive TPs re-surface as promoted “core” hits — product thesis *stale memory does not confirm* is violated on the paging path (critic already demotes; inject did not).

## Pattern

| Layer | Role |
|-------|------|
| `superseded_index` multi-hop | ids/themes dead for path seeds |
| `filter_superseded_hits` | quarantine matched archival hits |
| promote section | F145 filtered_n + do-not-re-raise |
| env | `TORII_ARCHIVAL_SUPERSEDE_FILTER=1` (0=off) |

## Success

- Fixture f145_ok: pickle-cold supersedes → not in promote core; section mentions F145
- Privacy: no `/Users/` in supersede meta
- f144_ok still holds with filter off for expand proof
