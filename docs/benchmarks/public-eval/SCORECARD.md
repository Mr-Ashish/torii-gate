<!-- torii-public-eval-scorecard -->

# Public labeled eval scorecard

_Generated: `2026-08-01T18:07:15Z` · seed **42** · model **`deepseek/deepseek-chat-v4-pro`** · target **8.5/10**_

**public_eval_ok:** `True`

Public labeled eval: Juice Shop synthetic + NodeGoat-theme + Django/Flask-theme packs; fixed seed; cost/PR from dogfood vault.

## Packs (license-safe synthetic · OSS themes)

| Pack | Cases | Theme |
|------|------:|-------|
| `django-vuln-synthetic` | 5 | Django/Flask training apps (generic) |
| `insecure-demo` | 4 | Ground truth for demo/insecure/app.py intentional vulns (Torii Gate dogfood). |
| `juice-shop-synthetic` | 5 | License-safe Juice Shop–theme ground truth for demo/juice-shop-synthetic (not a Juice Shop fork). |
| `nodegoat-synthetic` | 4 | OWASP NodeGoat |

## Offline labeled FP / TP

TP = required cases matched on good harness. FP proxy = weak harness recall (should stay ~0).

| Metric | Value |
|--------|------:|
| labeled_tp_cases | 18 |
| good_recall_mean | 1.0 |
| weak_recall_mean (FP proxy) | 0.0 |
| delta_recall_mean | 1.0 |
| packs_passed / total | 4 / 4 |
| all_pass | True |

### Per-pack

| pack | good_recall | weak_recall | delta | tp_promoted | pass |
|------|------------:|------------:|------:|------------:|:----:|
| insecure-demo | 1.0 | 0.0 | 1.0 | 4 | True |
| juice-shop-synthetic | 1.0 | 0.0 | 1.0 | 5 | True |
| nodegoat-synthetic | 1.0 | 0.0 | 1.0 | 4 | True |
| django-vuln-synthetic | 1.0 | 0.0 | 1.0 | 5 | True |

## Cost / PR (live dogfood vault)

Live OSS dogfood unlabelled; cost when hermes-usage present. Local hub vault only — never federated (see enterprise/PRIVACY.md).

| Stat | time-to-signal (s) | cost USD |
|------|-------------------:|---------:|
| n | 72 | 34 |
| mean | 101.711 | 0.017 |
| p50 | 93.0 | 0.014 |
| min | 39.2 | 0.008 |
| max | 262.0 | 0.058 |

Dogfood runs: **77** · source: `docs/benchmarks/traces vault dogfood`

Day-2: `python3 scripts/torii.py ops -- status` · [cost-pr-dashboard.md](../ops/cost-pr-dashboard.md) · commercial Cost honesty: [commercial-scorecard.md](../commercial-scorecard.md).

## Requirements checklist

- Juice Shop synthetic: **True**
- Additional OSS-theme packs: `django-vuln-synthetic, nodegoat-synthetic` ok=**True**
- Fixed seed: **42**
- Model id: **`deepseek/deepseek-chat-v4-pro`**
- Cost samples (hermes-usage): **34**

## Reproduce

```bash
export TORII_PUBLIC_EVAL_SEED=42
export TORII_MODEL=deepseek/deepseek-chat-v4-pro
python3 scripts/public_eval.py report
python3 scripts/public_eval.py fixture
python3 scripts/bench_corpus.py all
```

Related: [`docs/GOLDEN-PATH.md`](../../GOLDEN-PATH.md) · [`docs/benchmarks/golden-path-metrics.md`](../golden-path-metrics.md)
