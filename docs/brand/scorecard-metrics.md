# Torii Gate — measured scorecard (F129/F130/F164/F170)

_Generated: `2026-08-01T12:13:16Z` · level **L2** · brand_ready=True_

Measured gate readiness: dual compound (skill+memory) + workflow graph + demote_rate=None + memory_util_delta=None + hub-archival loop (util→reprompt→fitness→hub inject).

| Metric | Value |
|--------|------:|
| doctor_pass | True |
| recovery_ok | True |
| recovery_hub_gap_ok | True |
| skill_loop_level | L3 |
| memory_loop_level | L3 |
| workflow_level | L3 |
| workflow_valid | True |
| dual_compound_triple_ready | True |
| critic_approve_demote_rate | None |
| weak_approve_demoted | None |
| hub_gap_idle_demoted | None |
| recon_warm_hub_idle_demoted | None |
| recon_warm_hub_ok | True |
| memory_tool_util_delta | None |
| memory_tool_util_good | None |
| memory_tool_util_weak | None |
| hub_archival_util_ok | True |
| hub_archival_util_critic_ok | True |
| hub_archival_hub_ok | True |
| hub_archival_hub_inject_ok | True |
| hub_archival_fitness_ok | True |
| reprompt_adaptive_ok | True |
| router_synth_ok | True |
| hub_archival_loop_ok | True |
| hub_archival_hub_pressure_idle_demoted | None |
| skill_refine_ok | True |
| skill_refine_attr_ok | True |
| refine_dual_ok | True |
| refine_promote_ok | True |
| refine_dual_hub_ok | True |
| refine_loop_ok | True |
| refine_dual_fail_idle_demoted | None |

Source: `python3 scripts/torii.py scorecard` · workflow F131 · demote F128/F151 · util F130 · hub-archival F155–F163 (F164) · GEPA refine F165–F169 (F170 brand pack).

These are **measured** offline/ops metrics — not marketing pass rates.
