# Torii Gate — measured scorecard (F129/F130)

_Generated: `2026-08-01T07:10:59Z` · level **L3** · brand_ready=True_

Measured gate readiness: doctor + hub-gap critic + demote_rate=1.0 + memory_util_delta=0.85.

| Metric | Value |
|--------|------:|
| doctor_pass | True |
| recovery_ok | True |
| recovery_hub_gap_ok | True |
| skill_loop_level | L3 |
| memory_loop_level | L3 |
| critic_approve_demote_rate | 1.0 |
| weak_approve_demoted | True |
| hub_gap_idle_demoted | True |
| memory_tool_util_delta | 0.85 |
| memory_tool_util_good | 1.0 |
| memory_tool_util_weak | 0.15 |

Source: `python3 scripts/torii.py scorecard` · demote F128 · memory util F130.

These are **measured** offline/ops metrics — not marketing pass rates.
