# F136 research note — Scorecard skill utilization (inject ≠ use)

**Date:** 2026-08-01  
**Fire:** F136

## Sources

1. Mem2Act / SkillsBench / F121: inject presence ≠ utilization — score tool hits.
2. Ragas ToolCallAccuracy / agent eval 2026: measure mid-run tool selection.
3. CoEvoSkills: adopted skills need verification feedback or they idle.
4. F132–F135 propose/adopt/federate/fitness scorecard skills without mid-run util.

## Pattern

| Layer | Role |
|-------|------|
| skill-router.json | selected scorecard-gap skill ids |
| skill-hits.json | tool_hit per scorecard skill |
| score_scorecard_util | util_rate; gap if injected & tool_hit_n=0 |
| federate | scorecard-util-signals.json (ids + bins only) |
| F78 panel | f136_scorecard_util weight 0.06 |
| demote | APPROVE + gap → COMMENT (`scorecard_skill_idle_no_tool_hit`) |
| trajectory | soft ops_bonus ±0.03 from util |

## Commands

```bash
python3 scripts/skill_router.py scorecard-util --out-dir "$OUT_DIR"
```

## Env

- `TORII_SCORECARD_UTIL_FEDERATE=1` (default)

## Success

- Fixture: good util_rate=1; gap when idle; none-injected ok; privacy_ok
- Critic demotes APPROVE when scorecard skills idle
- No `/Users/` or raw tenant strings
