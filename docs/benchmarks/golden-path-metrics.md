<!-- torii-golden-path-metrics -->

# Golden path metrics

_Generated: `2026-08-01T14:14:46Z` · feature **GOLDEN** · target **7.5/10 commercial**_

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
| n | 39 |
| mean | 99.613 |
| p50 | 91.3 |
| min | 40.7 |
| max | 208.6 |

## Cost / PR (when hermes-usage present)

| Stat | USD |
|------|----:|
| n | 7 |
| mean | 0.011 |
| p50 | 0.012 |
| min | 0.008 |
| max | 0.016 |

## Verdict distribution (unlabelled live)

| Verdict | count |
|---------|------:|
| COMMENT | 1 |
| REQUEST_CHANGES | 17 |
| UNKNOWN | 26 |

## FP / TP chart (labeled offline)

TP = required cases caught on good (vulnerable) harness. FP proxy = weak harness recall (should stay near 0). Live OSS dogfood verdicts are unlabelled — not counted as TP/FP.

| Metric | Value |
|--------|------:|
| labeled_tp_cases | 9 |
| tp_rate (good harness recall) | 1.0 |
| fp_proxy (weak harness recall) | 0.0 |
| delta_recall | 1.0 |
| labeled packs all_pass | True |

### Packs

| pack | good_recall | weak_recall | delta | tp_promoted |
|------|------------:|------------:|------:|------------:|
| insecure-demo | 1.0 | 0.0 | 1.0 | 4 |
| juice-shop-synthetic | 1.0 | 0.0 | 1.0 | 5 |

## Recent dogfood rows

| trace | repo | pr | verdict | t_s | cost_usd | model | host |
|-------|------|---:|---------|----:|---------:|-------|------|
| `20260801-0255-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 |  | 79.8 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0305-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 |  | 158.8 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0315-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 |  | 95.6 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0320-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 |  | 110.3 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0330-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 |  | 86.2 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0335-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 |  | 83.4 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0340-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 |  | 82.5 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0345-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 |  | 92.3 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0350-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 | REQUEST CHANGES | 48.4 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0359-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 | REQUEST CHANGES | 40.7 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0407-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 | REQUEST CHANGES | 148.7 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0415-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 | REQUEST CHANGES | 147.0 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0424-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 | REQUEST CHANGES | 208.6 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0429-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 | REQUEST CHANGES | 196.0 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0435-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 | REQUEST CHANGES | 151.4 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0441-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 | REQUEST CHANGES | 163.8 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0448-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 |  | 164.1 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0455-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 |  | 156.5 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-0505-pytorch-pytorch-PR191813-m` | pytorch/pytorch | 191813 | REQUEST CHANGES | 82.9 | None | deepseek/deepseek-v4-pro | modal |
| `20260801-1413-pytorch-pytorch-PR191840-m` | pytorch/pytorch | 191840 | COMMENT | 48.0 | None | deepseek/deepseek-chat-v4-pr | modal |

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
