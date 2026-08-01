# F82 research note — safe skill auto-adopt

**Date:** 2026-08-01  
**Fire:** F82

## Sources

1. SkillOpt / Hermes self-evolution: held-out validation before adopt.
2. Loop Engineering: default REJECT; verifier before promoting artifacts.
3. Prior Torii: F74 proposals `validated_adopt` but never entered `active/`.

## Pattern

| Gate | Purpose |
|------|---------|
| F74 validate | structure/safety/keyword score |
| F78 critic fixture | panel still separates good/weak |
| F74 fitness fixture | malicious still rejected |
| Post-adopt re-run | rollback if fixtures break |

Default **off** (`TORII_SKILL_AUTO_ADOPT=0`).
