# F161 research note — Multi-tenant hub-archival gap pressure

**Date:** 2026-08-01  
**Fire:** F161

## Sources

1. FederatedSkill / multi-tenant util themes (privacy-safe bins only).
2. Torii F126 recovery hub gap_pressure + F125 always priority compound.
3. F155–F160 hub-archival util/reprompt/fitness/synth stack.

## Gap

Local hub-archival util is measured (F155) and demoted (F156) but multi-tenant chronic under-use did not compound into always priority or re-prompt bias.

## Pattern

| Layer | Role |
|-------|------|
| load_hub_archival_hub_signals | recovery-util + hub-archival-util-signals |
| post_score_hub_archival_hub | gap_pressure + priority_delta |
| decide_recovery_reprompt | F161 tags + hub_archival_hub_pressure_idle |
| select always | ha hub delta keeps skill under F119 budget |
| fitness federate | chronic gap → hub-archival-util-signals.json |
| F156 critic | deeper demote score when multi-tenant high |

## Success

- Fixture f161_ok: gap_pressure≥0.3, delta≥5, re-prompt with hub pressure tag
- Local ok util does not re-prompt
