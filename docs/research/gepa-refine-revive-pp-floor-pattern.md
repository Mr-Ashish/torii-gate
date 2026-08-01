# F177 — contribution_pp floor for dual_pass revive (SkillOpt gate)

## Sources
- Hermes self-evolution / SkillOpt: validation-gated recovery after reject — metrics must improve.
- GEPA (arXiv 2507.19457): reflective evolution re-entry needs evidence, not flag-only dual_pass.
- Assay / SkillsBench: contribution measurement over inject-only success.
- Torii F175–F176: dual_pass revive + free-rider MT gate still allowed tool_pp≈ε to re-boost.

## Insight
effective_pass (tool_pp>0) is too weak for always re-entry. Highest ROI: min `refine_tool_contribution_pp` floor (default 10) for local revive + multi-tenant promote; critic demote low-pp recovery APPROVE.

## Ship
- `refine_dual_revive_pp_gate_enabled` + `TORII_REFINE_REVIVE_MIN_PP`
- ingest sets `revive_pp_blocked` when dual_pass below floor
- promote_refine_dual_revive requires tool_pp ≥ floor
- f177 critic + demote-eval `low_pp_revive_idle_approve`
- fixture-refine-revive-pp; refine_loop_ok AND F177

## Metric
- Offline: low_pp blocked, high_pp revive, promote low blocked / high ok; demote-eval low_pp_revive_idle_demoted
- Live: Modal BIT3 + hermes F177 notice
