<!-- torii-cost-pr-dashboard -->

# Cost / PR dashboard (stub)

_Generated: `2026-08-01T14:37:05Z` · from dogfood vault_

Operator-facing cost visibility without opening Modal artifacts.

| Metric | Value |
|--------|------:|
| dogfood runs | 48 |
| time-to-signal p50 (s) | 84.3 |
| time-to-signal mean (s) | 95.286 |
| cost/PR p50 (USD) | 0.012 |
| cost/PR mean (USD) | 0.011 |
| cost/PR min–max | 0.008 – 0.016 |

### Verdict distribution (unlabelled live)

| Verdict | count |
|---------|------:|
| COMMENT | 5 |
| REQUEST_CHANGES | 17 |
| UNKNOWN | 26 |

Soft budget (GHA): set repo var `TORII_MAX_COST_USD` for over-budget warnings (does not fail the run by default).

Related: `docs/benchmarks/golden-path-metrics.md` · `docs/benchmarks/public-eval/SCORECARD.md`
