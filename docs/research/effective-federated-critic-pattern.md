# F95 research note — Effective-aware critic + federated strength signals

**Date:** 2026-08-01  
**Fire:** F95  
**Memory OSS:** Mem0/Zep temporal strength + F77 multi-tenant privacy — patterns only

## Sources

1. F94 consolidation: `effective = importance × half-life decay`.
2. F77 hub federation: theme/CWE/keywords/basenames + tenant_hash only.
3. Dual-pass critic (F70): TP keyword match + path → `confirmed_tp` without temporal strength.
4. Agent memory surveys (2026): high-hit stale facts poison retrieval/ranking.

## Pattern ported

| Idea | Torii F95 |
|------|-----------|
| Temporal strength in checker | dual_pass confirms TP only if `effective_score ≥ floor` (default 0.25) |
| Stale match | `stale_tp_match` status — path evidence only, no precision inflate |
| Federated strength | `effective_score` / `importance_score` privacy-safe floats on hub signals |
| Max-merge | cross-tenant max effective kept; promote can filter `min_effective` |
| Export | `memory_consolidate federate` → F77 ingest |

## Wire

- `bench_security_gate.dual_pass_critic` effective-aware
- `federated_hub_ingest` sanitize/merge/promote/INDEX
- post-review stage after F94 consolidate
- F78 panel surfaces `effective_precision` / `stale_tp_match`

## Success

- high effective → confirmed_tp; low effective → stale_tp_match
- federated fixture: max-merge 0.82 + min_effective promote
- privacy still holds (no paths/snippets)
