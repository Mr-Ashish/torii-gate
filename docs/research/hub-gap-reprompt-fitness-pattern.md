# F126 research note — Hub gap_pressure re-prompt + fitness ingest

**Date:** 2026-08-01  
**Fire:** F126

## Sources

1. **FederatedSkill** (arXiv 2606.03143): multi-tenant themes compound only when they change runtime policy (re-prompt + fitness).
2. **HASP** (arXiv 2605.17734): skills as interventions — hub gap pressure must intervene in the agent loop.
3. **MMG2Skill**: early-stop / budget — F108 still caps paid retries; hub bias does not add extra slots.
4. Loop-eng measure→feedback: F125 priority inject without re-prompt/fitness left partial util unaddressed.

## Pattern

| Layer | Role |
|-------|------|
| F125 hub-score | priority_delta + gap_pressure |
| F126 decide | partial util + gap_pressure ≥ thr → reprompt idle |
| F122 write | prompt notes hub gap pressure |
| F108 budget | still max_extra (default 1) |
| fitness | ingest_hub_recovery soft tool_hit shield |

## Env

- `TORII_HUB_GAP_REPROMPT=1` (default)
- `TORII_HUB_GAP_PRESSURE_THR=0.34`
- `TORII_SKILL_FITNESS_HUB=1` (default)

## Success

- Partial util + high hub gap → reprompt=1 hub_gap_bias=1
- Full util → no re-prompt
- Fitness ingest_n ≥ 1 privacy_ok
