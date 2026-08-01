# F93 research note — Mem0 ADD/UPDATE/DELETE/NONE write policy

**Date:** 2026-08-01  
**Fire:** F93  
**Memory OSS:** oss-memory-mem0 (Apache-2.0) — patterns only

## Sources

1. Mem0 `DEFAULT_UPDATE_MEMORY_PROMPT`: ADD | UPDATE | DELETE | NONE per fact.
2. Mem0 supersession / linked_memory_ids: deleted memories must not resurface.
3. Torii F75 conflict-at-recall; F70/F64 write path was naive merge.

## Pattern ported

| Mem0 idea | Torii F93 |
|-----------|-----------|
| ADD | new theme/id → append |
| UPDATE | same theme/id → merge keywords/paths, hits++ |
| NONE | exact duplicate → no structural change |
| DELETE | path-anchored FP supersedes overlapping TP |
| superseded_by | audit field on deleted TP |

## Wire

- `merge_tp_signatures` prefers event policy when `TORII_MEMORY_EVENTS=1`
- CLI: plan / apply / promote / fixture / status

## Success

- fixture: NONE+UPDATE+ADD+DELETE+supersede
- bench_security_gate fixture still pass
