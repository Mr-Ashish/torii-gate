# Torii Gate — measured scorecard (F129/F130/F164/F170/F184)

_Generated: `2026-08-01T13:49:38Z` · level **L3** · brand_ready=True_

Measured gate readiness: dual compound (skill+memory) + workflow graph + demote_rate=1.0 + memory_util_delta=0.85 + hub-archival loop (util→reprompt→fitness→hub inject).

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
| critic_approve_demote_rate | 1.0 |
| weak_approve_demoted | True |
| hub_gap_idle_demoted | True |
| recon_warm_hub_idle_demoted | True |
| recon_warm_hub_ok | True |
| memory_tool_util_delta | 0.85 |
| memory_tool_util_good | 1.0 |
| memory_tool_util_weak | 0.15 |
| hub_archival_util_ok | True |
| hub_archival_util_critic_ok | True |
| hub_archival_hub_ok | True |
| hub_archival_hub_inject_ok | True |
| hub_archival_fitness_ok | True |
| reprompt_adaptive_ok | True |
| router_synth_ok | True |
| hub_archival_loop_ok | True |
| hub_archival_hub_pressure_idle_demoted | True |
| skill_refine_ok | True |
| skill_refine_attr_ok | True |
| refine_dual_ok | True |
| refine_promote_ok | True |
| refine_dual_hub_ok | True |
| refine_loop_ok | True |
| refine_dual_decay_ok | True |
| refine_decay_fed_ok | True |
| refine_dual_fail_idle_demoted | True |
| refine_decay_hub_idle_demoted | True |
| refine_dual_revive_ok | True |
| free_rider_revive_ok | True |
| revive_pp_gate_ok | True |
| free_rider_revive_idle_demoted | True |
| low_pp_revive_idle_demoted | True |
| revive_loo_gate_ok | True |
| loo_revive_idle_demoted | True |
| hub_gepa_compound_ok | True |
| hub_gepa_compound_idle_demoted | True |
| hub_gepa_compound_inject_ok | True |
| hub_gepa_compound_always_ok | True |
| reprompt_compound_ok | True |

Source: `python3 scripts/torii.py scorecard` · workflow F131 · demote F128/F151 · util F130 · hub-archival F155–F163 (F164) · GEPA refine F165–F180 (F170/F180).

These are **measured** offline/ops metrics — not marketing pass rates.
