# F175 — dual_pass revive after multi-tenant decay

## Sources
- GEPA (arXiv 2507.19457): reflective evolution needs recoverability — failed variants can re-enter via dual_pass evidence, not permanent blacklist.
- FederatedSkill: multi-tenant gates for promote *and* demote; recovery must also multi-tenant gate free-rider re-boost.
- Torii F171–F173: chronic dual_fail decay + federate amplify + critic demote left `multi_tenant_decay` sticky with no re-boost path.
- Hermes self-evolution / SkillOpt: validation-gated skill best can recover after reject when metrics improve.

## Insight
Decay without revive is a one-way trap. Highest ROI after F173: **dual_pass after prior decay → clear multi_tenant_decay, federate privacy-safe revive bins, multi-tenant re-boost always priority, supersede decay themes.**

## Ship
- `ingest_refine_dual` F175 local revive (streak/rate recovery)
- `federate_refine_dual_revive` / `promote_refine_dual_revive`
- router always Δprio from revive themes + ledger flags
- hermes soft `federate-refine-revive` + `promote-refine-revive`
- `refine_dual_revive_ok` + `refine_loop_ok` AND F175
- fixture `fixture-refine-revive`

## Metric
- Offline: local_revive + multi_tenant promote + decay supersede + privacy_ok
- Live: util_rate / recall; hermes F175 soft notices
