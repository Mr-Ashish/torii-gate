# Fire — F43 preflight cost (2026-07-31)

## Problem

F29 budget is post-hoc (spend already happened). Large PRs on Opus can still
start a multi-dollar agent loop before any soft alert.

## Hermes / industry inspiration

H6: hard preflight spend estimate before Hermes — refuse or force cheap model
when diff huge + budget tight.

## Ship

- `scripts/preflight_cost.py` estimate/decide (token proxy × model $/MTok table)
- Default action `force_cheap` when `TORII_MAX_COST_USD` set and estimate over
- Refuse when already cheap still over, or `TORII_PREFLIGHT_ACTION=refuse`
- `run-hermes-review.sh` skips Hermes install + loop on refuse (stub COMMENT)
- pack signals + Run Console; workflow/Modal/install

## Verify

```bash
pytest tests/test_preflight_cost.py tests/test_pack_run_for_ui.py -q
bash -n scripts/run-hermes-review.sh
TORII_MAX_COST_USD=0.05 python3 scripts/preflight_cost.py decide \
  --model anthropic/claude-opus-5 --diff-bytes 200000 --file-count 20
```
