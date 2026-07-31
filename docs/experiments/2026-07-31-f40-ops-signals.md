# Fire — F40 ops signals in run-bundle + Run Console (2026-07-31)

## Problem

Operators packing a run into the Run Console still could not see **why** a run
was free-skipped, timed out, over budget, or truncated without grepping
artifacts. F36/F38/F29/F27 wrote evidence; the UI ignored it.

## Ship

- `pack-run-for-ui.py` → `bundle.signals` (timeout, path_skip, over_budget, diff_truncated, flags)
- GHA path-skip + Modal path-skip write `ops-signals.env` for durable pack
- Run Console header chips + Overview **Ops signals (F40)** panel
- Tests + fixture rebuild

## Verify

```bash
pytest tests/test_pack_run_for_ui.py -q
cd ui/review-console && npm run pack-fixture && npm run build
```
