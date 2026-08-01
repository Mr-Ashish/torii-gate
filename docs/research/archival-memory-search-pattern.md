# F98 research note — MemGPT archival_memory_search + promote-to-core

**Date:** 2026-08-01  
**Fire:** F98  
**Memory OSS:** MemGPT/Letta archival search patterns only

## Sources

1. MemGPT `archival_memory_search` / `core_memory_append` — agent pages cold facts into working context.
2. Torii F97 archival tier existed without a retrieval path.
3. MEMORY.md distill is append-only prose — not path-queryable for PR basenames.

## Pattern

| MemGPT idea | Torii F98 |
|-------------|-----------|
| archival_memory_search | keyword score over TP/FP/federated + MEMORY.md |
| promote to core | inject section for current PR prompt |
| auto from paths | basenames of changed files as query |
| privacy | drop /Users and secret-like tokens from index |

## Wire

- `scripts/archival_memory_search.py` search/promote/auto/fixture
- assemble-context soft after F75
- memory_loop stage `archival_search`
- toggle `TORII_ARCHIVAL_SEARCH`

## Success

- fixture: TP+FP+MEMORY hits; privacy; auto from paths
- memory_loop L3; smoke PASS
