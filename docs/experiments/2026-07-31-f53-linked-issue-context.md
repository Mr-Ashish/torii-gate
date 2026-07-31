# F53 — Linked issue context (ISSUE_CTX)

**Date:** 2026-07-31  
**Status:** shipped (control-plane + prompt)  
**Tag:** PRODUCT_FEATURE | AGENT_QUALITY

## Problem

Reviews often miss **claim-to-fix** intent when the PR only links `Fixes #N` without
restating acceptance criteria. Severity calibration (F50) already treats “claims to
fix” seriously for tests, but the model rarely sees the issue body/comments unless
it spends tool turns on `gh issue view`.

## Fix (minimal)

1. **`scripts/linked_issue_context.py`:** extract refs (`Fixes/Closes/Resolves #N`,
   cross-repo `owner/repo#N`, issue URLs, bare `#N`, optional head-branch `N-slug`);
   fetch via `gh issue view` or `TORII_ISSUE_CONTEXT_FIXTURE`; format markdown;
   write `linked-issues.md` + `linked-issue-context.env`.
2. **`assemble-context.sh`:** soft assemble after `pr.json`; inject into `context.md`
   and `{{LINKED_ISSUES}}` in the review prompt.
3. **`agent/review-prompt.md` + `SOUL.md` + `MEMORY.seed`:** use linked issues as
   acceptance criteria; still untrusted.
4. **Pack chip** `issue-ctx` when `fetched>0`; save-trace copies env + md.
5. **Toggle** `TORII_ISSUE_CONTEXT=1` (default); caps for count/body/comments.

No second Hermes loop. Soft: network/fetch failure never blocks assemble.

## Tests

`tests/test_linked_issue_context.py`  
`tests/test_pack_run_for_ui.py::test_f53_issue_context_signal`

## Next

Live mini e2e on an eval PR that `Fixes #N` (or fixture-backed local assemble) to
measure D8 Memory/context lift; then PR description filler / incremental / thread.
