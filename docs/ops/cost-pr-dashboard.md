<!-- torii-cost-pr-dashboard -->

# Cost / PR dashboard (stub)

_Generated: `2026-08-01T15:05:15Z` · from dogfood vault_

Operator-facing cost visibility without opening Modal artifacts.

| Metric | Value |
|--------|------:|
| dogfood runs | 52 |
| time-to-signal p50 (s) | 84.3 |
| time-to-signal mean (s) | 97.813 |
| cost/PR p50 (USD) | 0.012 |
| cost/PR mean (USD) | 0.017 |
| cost/PR min–max | 0.008 – 0.058 |

### Verdict distribution (unlabelled live)

| Verdict | count |
|---------|------:|
| COMMENT | 7 |
| REQUEST_CHANGES | 19 |
| UNKNOWN | 26 |

Soft budget (GHA): set repo var `TORII_MAX_COST_USD` for over-budget warnings (does not fail the run by default).

Related: `docs/benchmarks/golden-path-metrics.md` · `docs/benchmarks/public-eval/SCORECARD.md`
