# F138 research note — Scorecard hub post-score compound

**Date:** 2026-08-01  
**Fire:** F138

## Sources

1. F125 recovery hub compound: federated util themes → always priority deltas.
2. FederatedSkill: share skill themes not trajectories across tenants.
3. F136/F134 federate scorecard util/ops; without post-score they never rank inject.
4. Loop-eng multi-loop coordination: measure → federate → prioritize next cycle.

## Pattern

| Layer | Role |
|-------|------|
| scorecard-util-signals.json | F136 multi-tenant util themes |
| post_score_scorecard_hub | skill_id → priority_delta (cap +40) |
| select_skills | score bump for hub-hit scorecard ops |
| inject | `<!-- torii-f138-scorecard-hub -->` section |
| fitness | soft ingest_scorecard_skills shield |
| CLI | scorecard-hub-score; hub-score includes nested scorecard_hub |

## Env

- `TORII_SCORECARD_HUB_COMPOUND=1` (default)

## Success

- Fixture: skill_n≥1, delta≥5, inject marker, privacy_ok
- No `/Users/` or raw tenant strings
