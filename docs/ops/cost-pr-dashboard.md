<!-- torii-cost-pr-dashboard -->

# Cost / PR dashboard

_Generated: `2026-08-01T17:58:28Z` · cost_ok=**True** · from dogfood vault_

Measured cost/PR + time-to-signal from live Modal dogfood (hermes-usage) with gate certificate ids — not a stub.

Buyer/ops: open this page instead of Modal run artifacts for p50 cost and signal latency.

| Metric | Value |
|--------|------:|
| dogfood runs | 76 |
| cost samples (hermes-usage) | 33 |
| time-to-signal p50 (s) | 93.0 |
| time-to-signal mean (s) | 100.623 |
| cost/PR p50 (USD) | 0.014 |
| cost/PR mean (USD) | 0.017 |
| cost/PR min–max | 0.008 – 0.058 |
| cost_ok (≥5 samples + p50) | True |

### Verdict distribution (unlabelled live)

| Verdict | count |
|---------|------:|
| APPROVE | 16 |
| COMMENT | 7 |
| REQUEST_CHANGES | 27 |
| UNKNOWN | 26 |

### Recent dogfood (cost × certificate)

| trace | pr | verdict | t_s | cost_usd | certificate | host |
|-------|---:|---------|----:|---------:|-------------|------|
| `20260801-1630-pytorch-pytorch-PR1918` | 191840 | APPROVE | 122.0 | 0.019598519000000002 | `gc-c1d8088ce9649d7a` | modal |
| `20260801-1636-pytorch-pytorch-PR1918` | 191840 | APPROVE | 112.0 | 0.017309839000000004 | `gc-c44356ac39c273bc` | modal |
| `20260801-1642-pytorch-pytorch-PR1918` | 191840 | APPROVE | 97.0 | 0.021760091999999998 | `gc-7d4a3cd3ec21d7e6` | modal |
| `20260801-1649-pytorch-pytorch-PR1918` | 191840 | APPROVE | 93.0 | 0.015617399 | `gc-23ee89e53f33b7d9` | modal |
| `20260801-1654-pytorch-pytorch-PR1918` | 191840 | REQUEST CHANGES | 97.0 | 0.024852913 | `gc-332eb8180a333c36` | modal |
| `20260801-1700-pytorch-pytorch-PR1918` | 191840 | REQUEST CHANGES | 93.0 | 0.013211675 | `gc-e7fe92916d5c3e59` | modal |
| `20260801-1706-pytorch-pytorch-PR1918` | 191840 | APPROVE | 89.0 | 0.018487964 | `gc-58da0b7175c81ccd` | modal |
| `20260801-1712-pytorch-pytorch-PR1918` | 191840 | APPROVE | 68.0 | 0.011242198000000002 | `gc-e9a820f99efec661` | modal |
| `20260801-1719-pytorch-pytorch-PR1918` | 191840 | APPROVE | 130.0 | 0.013063195 | `gc-5010f8293ba0375a` | modal |
| `20260801-1728-pytorch-pytorch-PR1918` | 191840 | APPROVE | 167.0 | 0.013160548 | `gc-4bb950ef6114e730` | modal |
| `20260801-1743-pytorch-pytorch-PR1918` | 191840 | APPROVE | 131.0 | 0.016311252999999998 | `gc-f77c5e29fda99ab8` | modal |
| `20260801-1753-pytorch-pytorch-PR1918` | 191840 | APPROVE | 108.0 | 0.011171234999999998 | `gc-61e9e283ea5a8716` | modal |

Soft budget (GHA): set repo var `TORII_MAX_COST_USD` for over-budget warnings (does not fail the run by default).

Refresh:

```bash
python3 scripts/ops_dashboard.py report
python3 scripts/golden_path_metrics.py report
python3 scripts/torii.py ops -- status
```

Related: [`golden-path-metrics.md`](../benchmarks/golden-path-metrics.md) · [`public-eval/SCORECARD.md`](../benchmarks/public-eval/SCORECARD.md) · [`GATE.md`](../GATE.md)
