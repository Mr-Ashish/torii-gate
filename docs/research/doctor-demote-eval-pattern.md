# F128 research note — Doctor recovery_hub_gap_ok + demote-eval paper metric

**Date:** 2026-08-01  
**Fire:** F128

## Sources

1. Agent eval 2026: recovery rate + validation pass rate sit next to task success (scoreboard metrics).
2. Loop-eng doctor: day-2 habit must surface critic demote path readiness.
3. F127 hub gap checker without scorecard/doctor is invisible to installers.
4. Paper vault needs demote_rate, not only BIT3_OK rows.

## Pattern

| Surface | Field |
|---------|--------|
| skill_loop scorecard | recovery_hub_gap_ok |
| torii doctor | fails closed if hub gap critic/demote-eval missing |
| demote-eval | critic_approve_demote_rate + weak/hub demote flags |
| traces | critic-demote-eval.json |

## Success

- doctor_pass with recovery_hub_gap_ok true
- demote-eval eval_pass; demote_rate ≥ 0.5 on APPROVE pack
