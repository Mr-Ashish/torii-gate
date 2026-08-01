# F92 research note — smoke skill-loop L3 + CI annotation

**Date:** 2026-08-01  
**Fire:** F92

## Gap

F91 scorecard existed but offline smoke stopped at F79; CI never surfaced skill-loop readiness.

## Pattern

1. `smoke-torii-gate.sh` step 6: `skill_loop_status fixture` → L3 (or shallow L2+ if `TORII_SMOKE_SKILL_LOOP=0`).
2. Reusable workflow after `torii/gate`: job summary block for skill loop.
3. Optional commit status `torii/skill-loop` only when `TORII_SKILL_LOOP_STATUS_COMMIT=1` (advisory success/neutral — not merge-blocking by default).

## Success

- smoke PASS includes skill_loop fixture L3
- workflow summary mentions route→hit→fitness→dual→attr→inject
