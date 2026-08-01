<!-- torii-golden-path-metrics -->

# Golden path metrics

_Generated: `2026-08-01T18:07:15Z` · feature **GOLDEN** · target **7.5/10 commercial**_

**One-liner:** install → required check torii/gate → real PR dogfood → FP/TP chart

**golden_path_ok:** `True` · readiness 15/15 (100.0%)

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
| n | 72 |
| mean | 101.711 |
| p50 | 93.0 |
| min | 39.2 |
| max | 262.0 |

## Cost / PR (when hermes-usage present)

| Stat | USD |
|------|----:|
| n | 34 |
| mean | 0.017 |
| p50 | 0.014 |
| min | 0.008 |
| max | 0.058 |

## Verdict distribution (unlabelled live)

| Verdict | count |
|---------|------:|
| APPROVE | 17 |
| COMMENT | 7 |
| REQUEST_CHANGES | 27 |
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
| `20260801-1546-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 94.0 | 0.026977046999999997 | `gc-82065e74ed27795d` | deepseek/deepseek-v4-pro | modal |
| `20260801-1552-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 97.0 | 0.032760314 | `gc-1bf7e01455b0a74d` | deepseek/deepseek-v4-pro | modal |
| `20260801-1558-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 128.0 | 0.023690680000000002 | `gc-68fb8575841855f5` | deepseek/deepseek-v4-pro | modal |
| `20260801-1605-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 117.0 | 0.022070682 | `gc-f0613e3b4d162c10` | deepseek/deepseek-v4-pro | modal |
| `20260801-1610-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 73.0 | 0.018905854 | `gc-966d68ed6c5808da` | deepseek/deepseek-v4-pro | modal |
| `20260801-1618-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 76.0 | 0.018294679 | `gc-089fed34e9eb71c5` | deepseek/deepseek-v4-pro | modal |
| `20260801-1624-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 117.0 | 0.023839971999999997 | `gc-c9f317b2365e7643` | deepseek/deepseek-v4-pro | modal |
| `20260801-1630-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 122.0 | 0.019598519000000002 | `gc-c1d8088ce9649d7a` | deepseek/deepseek-v4-pro | modal |
| `20260801-1636-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 112.0 | 0.017309839000000004 | `gc-c44356ac39c273bc` | deepseek/deepseek-v4-pro | modal |
| `20260801-1642-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 97.0 | 0.021760091999999998 | `gc-7d4a3cd3ec21d7e6` | deepseek/deepseek-v4-pro | modal |
| `20260801-1649-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 93.0 | 0.015617399 | `gc-23ee89e53f33b7d9` | deepseek/deepseek-v4-pro | modal |
| `20260801-1654-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 97.0 | 0.024852913 | `gc-332eb8180a333c36` | deepseek/deepseek-v4-pro | modal |
| `20260801-1700-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | REQUEST CHANGES | 93.0 | 0.013211675 | `gc-e7fe92916d5c3e59` | deepseek/deepseek-v4-pro | modal |
| `20260801-1706-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 89.0 | 0.018487964 | `gc-58da0b7175c81ccd` | deepseek/deepseek-v4-pro | modal |
| `20260801-1712-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 68.0 | 0.011242198000000002 | `gc-e9a820f99efec661` | deepseek/deepseek-v4-pro | modal |
| `20260801-1719-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 130.0 | 0.013063195 | `gc-5010f8293ba0375a` | deepseek/deepseek-v4-pro | modal |
| `20260801-1728-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 167.0 | 0.013160548 | `gc-4bb950ef6114e730` | deepseek/deepseek-v4-pro | modal |
| `20260801-1743-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 131.0 | 0.016311252999999998 | `gc-f77c5e29fda99ab8` | deepseek/deepseek-v4-pro | modal |
| `20260801-1753-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 108.0 | 0.011171234999999998 | `gc-61e9e283ea5a8716` | deepseek/deepseek-v4-pro | modal |
| `20260801-1800-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | APPROVE | 179.0 | 0.010264579000000001 | `gc-810df2f120dd4956` | deepseek/deepseek-v4-pro | modal |

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
