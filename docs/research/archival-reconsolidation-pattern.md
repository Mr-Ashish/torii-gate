# F146 research note — Archival reconsolidation on promote

**Date:** 2026-08-01  
**Fire:** F146

## Sources

1. Human-inspired agent memory (reconsolidation upon retrieval).
2. MemGPT/Letta: archival → core paging should compound durable state, not one-shot inject.
3. F145 supersede filter: only non-superseded hits may warm the store.

## Gap

F98/F144/F145 page cold hits into the prompt but leave `tp-signatures.json` unchanged. Retrieval without reconsolidation is write-only context tax — next PR re-pays the same cold score.

## Pattern

| Layer | Role |
|-------|------|
| filter (F145) | quarantine superseded first |
| reconsolidate_hits | hits++ / last_retrieved_at / soft eff bump |
| ledger | `.torii/archival-reconsolidation.json` (ids only) |
| env | `TORII_ARCHIVAL_RECONSOLIDATE=1` |

## Success

- Fixture f146_ok: sqli-arch hits 4→5, last_retrieved set, section F146, dead supersede not warmed
- Privacy: no `/Users/` in ledger
