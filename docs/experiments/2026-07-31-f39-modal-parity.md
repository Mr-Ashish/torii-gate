# Fire — F39 Modal host parity (2026-07-31)

## Problem

Modal `review_pr` was a second-class kitchen: no F38 path-skip before clone,
and no F22/F23/F9/F37 signals after review (comment only). GHA had the full
trust/cost stack; Modal burned OpenRouter on docs-only PRs and left PRs without
status/labels/inline.

## Ship

- `scripts/modal_parity.py` — pure path-skip preflight for Modal
- `review_pr`: list paths → F38 skip (stub + post + labels) **before** clone
- `review_pr`: after paid review → `report-verdict.sh` (status, PR review, inline, labels)
- Explicit `TORII_REVIEW_TIMEOUT_SECONDS` (F36) in Modal env
- Version `0.6.0-f39`

## Verify

```bash
pytest tests/test_modal_parity.py -q
python3 scripts/modal_parity.py path-skip --path README.md --globs docs; echo $?
```
