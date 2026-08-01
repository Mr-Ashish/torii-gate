# F103 research note — Unified torii_memory CLI front door

**Date:** 2026-08-01  
**Fire:** F103

## Sources

1. MemGPT/Letta: memory exposed as explicit agent-callable tools.
2. Torii F75–F102: many scripts; Hermes must invent invocations.
3. Loop-eng: discoverable entrypoints beat SOUL prose.

## Pattern

| Surface | Torii F103 |
|---------|------------|
| help | catalogs search/graph/tiers/loop/… |
| dispatch | `torii_memory.py <cmd> -- <args>` → script |
| doctor | soft fixture matrix for memory stack |
| inject-hint | assemble-context prompt card for Hermes |

## Success

- fixture: help + status + doctor + hint
- memory_loop L3 includes memory_cli stage
- smoke PASS
