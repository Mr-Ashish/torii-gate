# F59 — Incremental review

**Date:** 2026-07-31  
**Status:** shipped (MERGED PR #9)  
**Tag:** PRODUCT_FEATURE | DETERMINISTIC

## Problem

Re-reviewing an entire large PR on every push wastes tokens and re-litigates
settled findings. Need a code-scoped diff of **new commits only**.

## Fix

1. **`scripts/incremental_review.py`** — parse/format markers with `head=`; plan
   `full|incremental|unchanged`; assemble rewrites `pr.diff` + `files.txt` via
   GitHub compare API (or fixture).
2. **Assemble** soft-runs plan when enabled; injects `{{INCREMENTAL_NOTE}}`.
3. **Normalize** `--head-sha` stamps `<!-- torii-review pr=N run=R head=SHA -->`.
4. **Toggle** `TORII_INCREMENTAL` default **off** (safe).

## Tests

`tests/test_incremental_review.py`

## Verify

```bash
pytest tests/test_incremental_review.py -q
TORII_INCREMENTAL=1 python3 scripts/incremental_review.py plan --pr 1 --head-sha bbb --last-head aaa
```
