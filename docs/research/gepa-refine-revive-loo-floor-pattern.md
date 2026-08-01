# F179 — LOO attribution floor for dual_pass revive

## Sources
- Torii F89/F166 skill-attribution LOO free-rider demote.
- SkillOpt / Hermes self-evolution: validation-gated recovery.
- F177 tool_pp floor alone ignores free-riding skills with high dual_pp from pack probes.

## Insight
High refine_tool_contribution_pp can free-ride always re-entry when LOO marks the skill free_rider.
Highest ROI: block dual_pass revive when attribution free_rider or avg_contribution < floor after min_n.

## Ship
- `refine_dual_revive_loo_gate_enabled` + `_load_attr_skill`
- ingest sets `revive_loo_blocked`; positive LOO soft-boosts
- f179 critic + demote-eval `loo_revive_idle_approve`
- fixture-refine-revive-loo; refine_loop_ok AND F179

## Metric
- Offline: free_rider blocked, positive LOO revives; demote-eval loo_revive_idle_demoted
- Live: Modal BIT3 + hermes F179 notice
