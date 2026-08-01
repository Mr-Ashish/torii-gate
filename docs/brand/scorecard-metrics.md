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

## F137 scorecard util soft re-prompt

| Metric | Meaning |
|--------|---------|
| scorecard_reprompt | 1 when F136 gap triggers one paid soft re-run |
| scorecard_only | 1 when recovery util ok but scorecard idle |
| reason | scorecard_utilization_gap (+fed_gap) |

Source: `skill_router.py reprompt-decide` / Hermes F122 path.

## F138 scorecard hub compound

| Metric | Meaning |
|--------|---------|
| scorecard_hub_skill_n | Scorecard ops skills with hub tool-hit themes |
| priority_delta | Select/inject rank bump from multi-tenant util |
| gap_pressure | Federated scorecard util gap fraction |

Source: `python3 scripts/skill_router.py scorecard-hub-score`.

## F139 scorecard hub gap critic

| Metric | Meaning |
|--------|---------|
| scorecard_hub_gap_demote_ok | APPROVE demoted when hub gap + local idle |
| gap_pressure | Federated scorecard util gap fraction |

Source: `second_agent_critic.py` panel / `demote-eval`.

## F140 scorecard hub attribution floor

| Metric | Meaning |
|--------|---------|
| scorecard_floored | Skills LOO-floored from hub/fitness scorecard evidence |
| scorecard_contributors | Non free-rider scorecard hub skills |

Source: `skill_attribution.py attribute` / fixture.
