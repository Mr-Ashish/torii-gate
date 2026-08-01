# F110 research note — Unified product CLI front door

**Date:** 2026-08-01  
**Fire:** F110

## Sources

1. Loop Engineering `@cobusgreyling/loop`: thin umbrella, pass-through, doctor/status.
2. Torii F103: memory-only front door; peer scripts still tribal.
3. Hermes: agents need one discoverable product entrypoint.

## Pattern

| Surface | Torii F110 |
|---------|------------|
| help | groups memory/gate/budget/skill-loop/memory-loop/smoke |
| dispatch | `torii.py <group> -- <args>` → script |
| doctor | memory status + loops + budget fixture |
| inject-hint | assemble-context product CLI card |

## Success

- fixture: help + status + doctor + dispatch memory
- install ships `torii.py`
- soft assemble inject
