# F58 — PR description filler

**Date:** 2026-07-31  
**Status:** shipped (MERGED PR #8)  
**Tag:** PRODUCT_FEATURE | DETERMINISTIC

## Problem

Empty or placeholder PR bodies hurt review quality (missing intent, test plan,
file map). Full LLM `/describe` (pr-agent style) is costly and can overwrite
author prose; Torii needs a **safe, code-first** scaffold.

## Fix

1. **`scripts/pr_description_filler.py`** — type classify + file list + test-plan
   checklist + issue refs from title/body; optional F57 mermaid embed.
2. **Markers** `<!-- torii-description -->` … `<!-- /torii-description -->`.
3. **Modes:** `fill-empty` (default) | `markers` | `force`.
4. **Assemble** soft-writes `pr-description.md` + merged body; never auto-posts.
5. **Apply** CLI: `gh pr edit` only if `TORII_PR_DESCRIPTION_APPLY=1` or `--force-apply`.
6. **Toggles:** `pr_description`, `pr_description_apply`, `pr_description_mode`.

## Tests

`tests/test_pr_description_filler.py`

## Verify

```bash
pytest tests/test_pr_description_filler.py -q
python3 scripts/pr_description_filler.py scaffold --pr-json docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/pr.json | head
python3 scripts/pr_description_filler.py plan --pr-json ... --mode fill-empty
```
