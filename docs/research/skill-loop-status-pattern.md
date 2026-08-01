# F91 research note — skill loop readiness scorecard

**Date:** 2026-08-01  
**Fire:** F91

## Gap

F90 branded `route→hit→fitness→dual→attr→inject` but ops/install could not answer
"is the skill path ready on this checkout?" F79 scorecard covered pack scripts only.

## Pattern

| Check | Source |
|-------|--------|
| Stage scripts + pack list | skill_router/fitness/dual/attr/auto_adopt |
| Active skills ≥1 | agent/skills/active |
| Wiring | assemble-context + run-torii-review stages |
| Deep fixtures | dual/attr/router/fitness fixture soft |
| Levels | L0–L3 like Loop Engineering readiness |

## Surfaces

- `python3 scripts/skill_loop_status.py status|scorecard|fixture|markdown`
- `workflow_as_code scorecard` → skill_loop block
- install-guide embeds markdown
- `torii_gate_status.py --skill-loop-only` (ops; merge path unchanged)
