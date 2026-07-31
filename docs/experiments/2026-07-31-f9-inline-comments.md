# Fire — F9 path-anchored inline comments (2026-07-31)

## Problem

Reviews lived only as Markdown issue comments + a short F23 review; findings
were not visible on **Files changed**.

## Ship (minimal)

- `scripts/post-inline-comments.py` plan|post
- Map findings/blocking → first added line in `pr.diff`
- Wire via `report-verdict.sh` + reusable workflow env vars
- Soft-fail; default severity critical/high/blocking; max 6

## Verify

```bash
pytest tests/test_post_inline_comments.py -q
bash -n scripts/report-verdict.sh
python3 scripts/post-inline-comments.py plan \
  --review docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/review.md \
  --diff docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/pr.diff
```
