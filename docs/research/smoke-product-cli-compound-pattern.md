# F111 research note — Smoke + CI doctor + insecure compound/federate proof

**Date:** 2026-08-01  
**Fire:** F111

## Sources

1. F110 product CLI doctor — not yet in smoke/CI summary.
2. F104/F107 compound+federate — live pytorch PRs correctly federate 0; need dogfood proof.
3. Loop-eng: doctor is day-2 habit; CI job summary is the scorecard surface.

## Pattern

| Surface | Check |
|---------|--------|
| smoke [8/9] | `torii.py doctor` doctor_pass |
| smoke [9/9] | `memory_compound_write fixture` fixture_pass + fed_count≥1 |
| GHA summary | Product CLI doctor annotation |

## Success

- smoke PASS includes doctor + compound federate
- offline federate_signals≥1 on insecure-demo good review
