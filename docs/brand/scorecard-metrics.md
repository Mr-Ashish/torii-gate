# Torii Gate — measured scorecard (F129/F130)

_Generated: `2026-08-01T07:43:33Z` · level **L2** · brand_ready=True_

Measured gate readiness: dual compound (skill+memory) + workflow graph + demote_rate=None + memory_util_delta=None.

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
| memory_tool_util_delta | None |
| memory_tool_util_good | None |
| memory_tool_util_weak | None |

Source: `python3 scripts/torii.py scorecard` · workflow F131 · demote F128 · util F130.

These are **measured** offline/ops metrics — not marketing pass rates.

## F136 scorecard skill utilization

| Metric | Meaning |
|--------|---------|
| scorecard util_rate | tool_hit_n / scorecard_injected_n (1.0 if none injected) |
| utilization_gap | true when scorecard skills injected but zero tool hits |
| federate | privacy-safe scorecard-util-signals.json |

Source: `python3 scripts/skill_router.py scorecard-util --out-dir $OUT_DIR`.
