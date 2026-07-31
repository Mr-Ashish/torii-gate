# Fire — F37 verdict PR labels (2026-07-31)

## Problem

Reaction + commit status + formal PR review exist (F22/F23), but operators
cannot filter project boards / search / automation on Torii outcome without
parsing comment text.

## Ship

- `scripts/apply-verdict-labels.py` plan|apply
- Labels: `{prefix}:approve|request-changes|comment|error` (default prefix `torii`)
- Pipeline fail → always `error` (never green-wash APPROVE)
- Soft-fail; opt-out `TORII_PR_LABELS=0`
- Wired into `report-verdict.sh` + reusable workflow

## Verify

```bash
pytest tests/test_apply_verdict_labels.py -q
python3 scripts/apply-verdict-labels.py plan --verdict REQUEST_CHANGES
bash -n scripts/report-verdict.sh
```
