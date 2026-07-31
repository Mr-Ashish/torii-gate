# F50 / H20 — severity calibration (missing tests)

**Date:** 2026-07-31  
**Status:** shipped

## Problem

F49 mini on odoo eval **#2** recovered tools (0→23) and even *mentioned* float `format:false` test gaps under **Suggestions**, but still emitted **APPROVE 95**. GHA on the same PR correctly used **REQUEST CHANGES** because the new production alias was untested.

## Fix

1. **Prompt/SOUL (H20 guidance):** missing tests for new production behavior the PR claims to fix → **REQUEST CHANGES** + **Blocking**; multi-behavior PRs need tests per path; never APPROVE while asking for tests on new code.
2. **Control-plane gate:** `scripts/severity_calibration.py`
   - Detects self-reported gaps (`Relevant tests …: no`, “missing/add tests”, “enhance test coverage”, coverage gap lines).
   - On **APPROVE** + gap → **REQUEST CHANGES**, score cap **69**, F50 banner.
   - Env: `TORII_SEVERITY_CALIBRATION` (default on), `TORII_SEVERITY_SCORE_CAP` (default 69).
   - Wired after F45 in `run-hermes-review.sh`; pack chip `sev-cal`; install + save-trace.

## Offline corpus check

| Review | Gate | Action |
|--------|------|--------|
| #2 F49 | yes | match=`missing_tests:suggestions` → RC, 95→69 |
| #4 F49 | no | no_test_gap_signal (stays APPROVE) |
| #5 F49 | yes | match=`tests_no_line` → RC, 92→69 |

## Tests

`tests/test_severity_calibration.py` + pack signal test. SOUL preflight still clean under F46 scan.
