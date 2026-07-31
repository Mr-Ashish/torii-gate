# Fire — F9c GitHub apply-suggestion blocks (2026-07-31)

## Problem

Reviews already write concrete `### Code suggestions` with ```diff``` fences,
but authors still copy-paste. F9/F9b only post finding notes, not one-click apply.

## Ship

- Parse `### Code suggestions` in `post-inline-comments.py`
- Map suggestion `-` lines onto PR `+` lines → multi-line ```suggestion``` comments
- Cap `TORII_SUGGESTION_MAX` (default 3); opt-out `TORII_INLINE_SUGGESTIONS=0`
- Same soft-fail post path as F9 (fixture-testable)

## Verify

```bash
pytest tests/test_post_inline_comments.py -q
python3 scripts/post-inline-comments.py plan \
  --review docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/review.md \
  --diff docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/pr.diff
```
