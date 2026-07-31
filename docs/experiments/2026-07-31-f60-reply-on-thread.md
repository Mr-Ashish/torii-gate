# F60 — Reply on thread

**Date:** 2026-07-31  
**Status:** shipped (MERGED PR #10)  
**Tag:** PRODUCT_FEATURE | DETERMINISTIC

## Problem

Re-reviews create **new** top-level inline comments even when Torii already
opened a thread on the same path:line. Conversation fragments; humans lose
context.

## Fix

1. **`scripts/reply_on_thread.py`** — index prior Torii roots (`<!-- torii-inline -->`);
   match planned findings by `path_line` (near ≤5) or `path`; format follow-up body
   with `<!-- torii-inline-reply -->`; post via GitHub `in_reply_to`.
2. **`post-inline-comments.py`** — before F9 review batch, split matches → replies;
   remainder still new inlines.
3. **Toggle** `TORII_REPLY_ON_THREAD` default **on** (F55 registry).
4. **report-verdict** summary chips replies_posted.

## Tests

`tests/test_reply_on_thread.py`

## Verify

```bash
pytest tests/test_reply_on_thread.py -q
TORII_REPLY_FIXTURE=/tmp/r.json python3 scripts/reply_on_thread.py post \
  --planned planned.json --existing existing.json --repo o/r --pr 1
```
