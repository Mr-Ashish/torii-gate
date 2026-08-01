<!-- torii-cost-pr-dashboard -->

# Cost / PR dashboard (stub)

_Generated: `2026-08-01T16:08:35Z` · from dogfood vault_

Operator-facing cost visibility without opening Modal artifacts.

| Metric | Value |
|--------|------:|
| dogfood runs | 61 |
| time-to-signal p50 (s) | 91.95 |
| time-to-signal mean (s) | 99.486 |
| cost/PR p50 (USD) | 0.012 |
| cost/PR mean (USD) | 0.017 |
| cost/PR min–max | 0.008 – 0.058 |

### Verdict distribution (unlabelled live)

| Verdict | count |
|---------|------:|
| APPROVE | 5 |
| COMMENT | 7 |
| REQUEST_CHANGES | 23 |
| UNKNOWN | 26 |

Soft budget (GHA): set repo var `TORII_MAX_COST_USD` for over-budget warnings (does not fail the run by default).

Related: `docs/benchmarks/golden-path-metrics.md` · `docs/benchmarks/public-eval/SCORECARD.md`
