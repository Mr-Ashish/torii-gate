<!-- torii-cost-pr-dashboard -->

# Cost / PR dashboard

_Generated: `2026-08-01T16:51:50Z` · cost_ok=**True** · from dogfood vault_

Measured cost/PR + time-to-signal from live Modal dogfood (hermes-usage) with gate certificate ids — not a stub.

Buyer/ops: open this page instead of Modal run artifacts for p50 cost and signal latency.

| Metric | Value |
|--------|------:|
| dogfood runs | 68 |
| cost samples (hermes-usage) | 25 |
| time-to-signal p50 (s) | 92.3 |
| time-to-signal mean (s) | 99.384 |
| cost/PR p50 (USD) | 0.016 |
| cost/PR mean (USD) | 0.018 |
| cost/PR min–max | 0.008 – 0.058 |
| cost_ok (≥5 samples + p50) | True |

### Verdict distribution (unlabelled live)

| Verdict | count |
|---------|------:|
| APPROVE | 10 |
| COMMENT | 7 |
| REQUEST_CHANGES | 25 |
| UNKNOWN | 26 |

### Recent dogfood (cost × certificate)

| trace | pr | verdict | t_s | cost_usd | certificate | host |
|-------|---:|---------|----:|---------:|-------------|------|
| `20260801-1541-pytorch-pytorch-PR1918` | 191840 | REQUEST CHANGES | 110.0 | 0.010891733 | `gc-2dae34f4cc018daa` | modal |
| `20260801-1546-pytorch-pytorch-PR1918` | 191840 | REQUEST CHANGES | 94.0 | 0.026977046999999997 | `gc-82065e74ed27795d` | modal |
| `20260801-1552-pytorch-pytorch-PR1918` | 191840 | APPROVE | 97.0 | 0.032760314 | `gc-1bf7e01455b0a74d` | modal |
| `20260801-1558-pytorch-pytorch-PR1918` | 191840 | APPROVE | 128.0 | 0.023690680000000002 | `gc-68fb8575841855f5` | modal |
| `20260801-1605-pytorch-pytorch-PR1918` | 191840 | REQUEST CHANGES | 117.0 | 0.022070682 | `gc-f0613e3b4d162c10` | modal |
| `20260801-1610-pytorch-pytorch-PR1918` | 191840 | REQUEST CHANGES | 73.0 | 0.018905854 | `gc-966d68ed6c5808da` | modal |
| `20260801-1618-pytorch-pytorch-PR1918` | 191840 | APPROVE | 76.0 | 0.018294679 | `gc-089fed34e9eb71c5` | modal |
| `20260801-1624-pytorch-pytorch-PR1918` | 191840 | REQUEST CHANGES | 117.0 | 0.023839971999999997 | `gc-c9f317b2365e7643` | modal |
| `20260801-1630-pytorch-pytorch-PR1918` | 191840 | APPROVE | 122.0 | 0.019598519000000002 | `gc-c1d8088ce9649d7a` | modal |
| `20260801-1636-pytorch-pytorch-PR1918` | 191840 | APPROVE | 112.0 | 0.017309839000000004 | `gc-c44356ac39c273bc` | modal |
| `20260801-1642-pytorch-pytorch-PR1918` | 191840 | APPROVE | 97.0 | 0.021760091999999998 | `gc-7d4a3cd3ec21d7e6` | modal |
| `20260801-1649-pytorch-pytorch-PR1918` | 191840 | APPROVE | 93.0 | 0.015617399 | `gc-23ee89e53f33b7d9` | modal |

Soft budget (GHA): set repo var `TORII_MAX_COST_USD` for over-budget warnings (does not fail the run by default).

Refresh:

```bash
python3 scripts/ops_dashboard.py report
python3 scripts/golden_path_metrics.py report
python3 scripts/torii.py ops -- status
```

Related: [`golden-path-metrics.md`](../benchmarks/golden-path-metrics.md) · [`public-eval/SCORECARD.md`](../benchmarks/public-eval/SCORECARD.md) · [`GATE.md`](../GATE.md)
