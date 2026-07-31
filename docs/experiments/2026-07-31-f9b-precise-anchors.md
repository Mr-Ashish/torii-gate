# Fire — F9b precise inline anchors (2026-07-31)

## Problem

F9 always pinned comments to the **first** added line per file, so findings
about later hunks landed on the wrong place in Files changed.

## Ship

- Parse `path:LINE`, `#L`, `line N`, optional Line column
- Anchor to that line if it is a changed `+` line; else nearest; else first
- Prompt/SOUL: prefer `path:LINE` only when seen in the diff
- Tests: exact + nearest synthetic fixtures

## Verify

```bash
pytest tests/test_post_inline_comments.py -q
```
