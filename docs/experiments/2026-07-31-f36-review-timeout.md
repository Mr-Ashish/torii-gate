# Fire — F36 review wall-clock timeout (2026-07-31)

## Problem

A hung Hermes agent loop can run until the GHA job cap (90m) or Modal
function timeout (25m), burning OpenRouter continuously. Soft cost budget
(F29) only *annotates* after a finished run — it does not stop the loop.

## Ship

- `scripts/run-with-timeout.py` — portable process-group timeout (exit 124)
- Wire into `run-hermes-review.sh` (default **1500s**; `0`/`off` disables)
- On timeout: skip chat fallback (no double spend), clear partial output,
  honest failure stub + job-summary section
- `vars.TORII_REVIEW_TIMEOUT_SECONDS` on reusable workflow
- Install pack allowlist includes helper

## Verify

```bash
pytest tests/test_run_with_timeout.py -q
bash -n scripts/run-hermes-review.sh
python3 scripts/run-with-timeout.py resolve
```
