# F104 research note — Integrity-gated post-review memory compound

**Date:** 2026-08-01  
**Fire:** F104

## Sources

1. **AgenticCyOps** (arXiv 2603.09134): multi-agent attack surfaces collapse to **tool orchestration** and **memory management**.
2. **LASM** (arXiv 2604.23338): Memory Integrity Controls — write restrictions + consistency validation before durable store.
3. **Mem0 / F93**: ADD/UPDATE/DELETE/NONE event policy already in Torii.
4. **Loop-eng**: tools-as-code write path over SOUL prose; discoverable CLI stages.

## Gap

F70 promote + F93 events existed, but **live reviews** only appended narrative `MEMORY.md` (distill). Durable `tp-signatures.json` did not grow from path-evidenced agent findings automatically — and had no poison gate for absolute-home paths or secret-like blobs.

## Pattern

| Gate | Rule |
|------|------|
| status | only `path_evidenced` or `confirmed_tp` |
| path | relative path required; reject `/Users/` `/home/` |
| body | min length; max length; reject secret-like tokens |
| store | theme/keywords/path_globs + provenance only (no snippets) |
| write | F93 `plan_events` → `apply_events` |

## Success

- fixture: good promotes ≥1; weak ≪ good; poison rejected; store clean
- wired post-review before consolidate/graph
- `torii_memory.py compound` dispatch
- memory_loop stage `compound_write`
