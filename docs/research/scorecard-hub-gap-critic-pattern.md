# F139 research note — Scorecard hub gap critic

**Date:** 2026-08-01  
**Fire:** F139

## Sources

1. F127 hub gap critic: multi-tenant recovery gap_pressure + local idle → demote.
2. Loop-eng maker/checker: independent checker demotes weak APPROVE.
3. F136/F138 scorecard util + hub post-score without panel demote left gap inert.
4. Agent eval 2026: validation demote rate sits next to task success.

## Pattern

| Layer | Role |
|-------|------|
| post_score_scorecard_hub | gap_pressure from federated util bins |
| score_scorecard_util | local idle scorecard ops |
| f139_scorecard_hub_gap | checker weight 0.07 |
| decide_verdict | APPROVE → COMMENT on high+idle |
| demote-eval | scorecard_hub_gap_idle_approve case |

## Env

- `TORII_SCORECARD_HUB_GAP_CRITIC=1` (default)
- `TORII_SCORECARD_HUB_GAP_THR=0.34` (default)

## Success

- Fixture f139_ok + has_f139; demote-eval scorecard_hub_gap_demote_ok
- Privacy: skill ids + bins only
