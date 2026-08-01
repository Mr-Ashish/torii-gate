<!-- torii-golden-path-metrics -->

# Golden path metrics

_Generated: `2026-08-01T16:30:38Z` · feature **GOLDEN** · target **7.5/10 commercial**_

**One-liner:** install → required check torii/gate → real PR dogfood → FP/TP chart

**golden_path_ok:** `True` · readiness 12/12 (100.0%)

Commercial loop (not F-stack depth):

```text
install pack → OPENROUTER_API_KEY → branch protection requires torii/gate
    → @torii review this pr → time-to-signal + verdict + cost/PR
    → labeled FP/TP chart (offline) + live dogfood archive
```

Buyer doc: [`docs/GOLDEN-PATH.md`](../GOLDEN-PATH.md) · Gate contract: [`docs/GATE.md`](../GATE.md)

## Time-to-signal (live dogfood)

| Stat | seconds |
|------|--------:|
| n | 59 |
| mean | 98.936 |
| p50 | 91.7 |
| min | 39.2 |
| max | 262.0 |

## Cost / PR (when hermes-usage present)

| Stat | USD |
|------|----:|
| n | 21 |
| mean | 0.018 |
| p50 | 0.013 |
| min | 0.008 |
| max | 0.058 |

## Verdict distribution (unlabelled live)

| Verdict | count |
|---------|------:|
| APPROVE | 6 |
| COMMENT | 7 |
| REQUEST_CHANGES | 25 |
| UNKNOWN | 26 |

## FP / TP chart (labeled offline)

TP = required cases caught on good (vulnerable) harness. FP proxy = weak harness recall (should stay near 0). Live OSS dogfood verdicts are unlabelled — not counted as TP/FP.

| Metric | Value |
|--------|------:|
| labeled_tp_cases | 18 |
| tp_rate (good harness recall) | 1.0 |
| fp_proxy (weak harness recall) | 0.0 |
| delta_recall | 1.0 |
| labeled packs all_pass | True |

### Packs

| pack | good_recall | weak_recall | delta | tp_promoted |
|------|------------:|------------:|------:|------------:|
| insecure-demo | 1.0 | 0.0 | 1.0 | 4 |
| juice-shop-synthetic | 1.0 | 0.0 | 1.0 | 5 |
| nodegoat-synthetic | 1.0 | 0.0 | 1.0 | 4 |
| django-vuln-synthetic | 1.0 | 0.0 | 1.0 | 5 |

## Recent dogfood rows

| trace | repo | pr | verdict | t_s | cost_usd | cert | model | host |
|-------|------|---:|---------|----:|---------:|------|-------|------|
| `20260801-1418-pytorch-pytorch-PR191831-m` | pytorch/pytorch | 191831 | COMMENT | 50.3 | None |  | deepseek/deepseek-chat-v4-pr | modal |
| `20260801-1424-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | COMMENT | 52.8 | None |  | deepseek/deepseek-chat-v4-pr | modal |
| `20260801-1431-pytorch-pytorch-PR191831-m` | pytorch/pytorch | 191831 | COMMENT | 59.9 | None |  | deepseek/deepseek-chat-v4-pr | modal |
| `20260801-1436-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | COMMENT | 49.4 | None |  | deepseek/deepseek-chat-v4-pr | modal |
| `20260801-1442-pytorch-pytorch-PR191831-m` | pytorch/pytorch | 191831 | COMMENT | 39.2 | None |  | deepseek/deepseek-chat-v4-pr | modal |
| `20260801-1445-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | COMMENT | 52.7 | None |  | deepseek/deepseek-chat-v4-pr | modal |
| `20260801-1451-pytorch-pytorch-PR191836-m` | pytorch/pytorch | 191836 | REQUEST CHANGES | 262.0 | 0.05819163199999999 | `gc-3f3b2e2951a12451` | deepseek/deepseek-v4-pro | modal |
| `20260801-1502-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 146.0 | 0.013437352999999999 | `gc-95888668ca0a313d` | deepseek/deepseek-v4-pro | modal |
| `20260801-1511-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 120.0 | 0.013640527 | `gc-8284cb3b1acf87c9` | deepseek/deepseek-v4-pro | modal |
| `20260801-1519-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 130.0 | 0.011048217 | `gc-c32714dc2a1f620e` | deepseek/deepseek-v4-pro | modal |
| `20260801-1527-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 93.0 | 0.009592533 | `gc-8145e70dec5ab02f` | deepseek/deepseek-v4-pro | modal |
| `20260801-1535-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 85.0 | 0.008625876000000001 | `gc-d810cd398488ea3a` | deepseek/deepseek-v4-pro | modal |
| `20260801-1541-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 110.0 | 0.010891733 | `gc-2dae34f4cc018daa` | deepseek/deepseek-v4-pro | modal |
| `20260801-1546-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 94.0 | 0.026977046999999997 | `gc-82065e74ed27795d` | deepseek/deepseek-v4-pro | modal |
| `20260801-1552-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 97.0 | 0.032760314 | `gc-1bf7e01455b0a74d` | deepseek/deepseek-v4-pro | modal |
| `20260801-1558-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 128.0 | 0.023690680000000002 | `gc-68fb8575841855f5` | deepseek/deepseek-v4-pro | modal |
| `20260801-1605-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 117.0 | 0.022070682 | `gc-f0613e3b4d162c10` | deepseek/deepseek-v4-pro | modal |
| `20260801-1610-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 73.0 | 0.018905854 | `gc-966d68ed6c5808da` | deepseek/deepseek-v4-pro | modal |
| `20260801-1618-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 76.0 | 0.018294679 | `gc-089fed34e9eb71c5` | deepseek/deepseek-v4-pro | modal |
| `20260801-1624-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 117.0 | 0.023839971999999997 | `gc-c9f317b2365e7643` | deepseek/deepseek-v4-pro | modal |

## Required check

Prefer GitHub branch protection required status context **`torii/gate`** (security-aware open/closed via `scripts/torii_gate_status.py`).

## Refresh

```bash
python3 scripts/golden_path_metrics.py report
python3 scripts/golden_path_metrics.py fixture
python3 scripts/torii.py golden-path -- report
```

Live dogfood (no PR comment):

```bash
modal run modal_app/app.py --bit 3 --repo pytorch/pytorch --pr 191840 \
  --model deepseek/deepseek-v4-pro --no-post-comment
```

Source JSON: `python3 scripts/golden_path_metrics.py report --json` · vault `docs/benchmarks/traces`
