# F54 — Fix-it prompt per inline comment

**Date:** 2026-07-31  
**Status:** shipped (control-plane)  
**Tag:** PRODUCT_FEATURE | AGENT_QUALITY | ACTIONABILITY

## Problem

Authors see high-signal inline findings but still hand-translate them into agent
tasks. Actionability (benchmark D3) stalls: copy/paste of free-form review prose
is lossy (missing file/line, acceptance criteria, verify steps).

## Fix (minimal)

1. **`scripts/post-inline-comments.py` (F54):** for each planned **finding**
   comment, append a collapsible **Fix-it prompt** block:
   - file + line + severity + issue + trigger
   - acceptance criteria
   - how to fix
   - verify checklist
   - conventional commit message suggestion
   - marker `<!-- torii-fixit -->`
2. **Toggle** `TORII_FIXIT_PROMPTS=1` (default) | `0`/`off` to disable.
3. Plan JSON reports `fixit` count + `fixit_enabled`.
4. Inline review summary body mentions F54 when prompts are attached.

No second model call. Soft: never blocks post path.

## Tests

`tests/test_post_inline_comments.py::{test_f54_*}`

## Verify

```bash
pytest tests/test_post_inline_comments.py -q
python3 scripts/post-inline-comments.py plan \
  --review docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/review.md \
  --diff docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/pr.diff \
  --severity all | jq '{findings,suggestions,fixit,fixit_enabled}'
```

## Next

Optional: surface fix-it prompts in the top-level PR review body table; wire
`fixit` chip into pack-run-for-ui; live e2e measure Actionability lift.
