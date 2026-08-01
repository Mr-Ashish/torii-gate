# F76 multi-corpus security bench INDEX

Updated: `2026-08-01T14:25:56Z`

License-safe packs for offline recall/precision measurement.
OSS-theme packs are **synthetic original code** (themes only — not forks).
Public scorecard: [`docs/benchmarks/public-eval/`](../public-eval/).

| Pack | Lang | Cases | Paths OK | Source |
|------|------|------:|:--------:|--------|
| `insecure-demo` | py | 4 | yes | `demo/insecure` |
| `juice-shop-synthetic` | js | 5 | yes | `demo/juice-shop-synthetic` |
| `nodegoat-synthetic` | js | 4 | yes | `demo/nodegoat-synthetic` |
| `django-vuln-synthetic` | py | 5 | yes | `demo/django-vuln-synthetic` |

## Commands

```bash
python3 scripts/bench_corpus.py list
python3 scripts/bench_corpus.py all
python3 scripts/bench_corpus.py fixture --pack juice-shop-synthetic
python3 scripts/bench_corpus.py taint --pack juice-shop-synthetic
```

## Latest aggregate

- **insecure-demo**: fixture_pass=True good_recall=1.0 weak_recall=0.0 delta=1.0
- **juice-shop-synthetic**: fixture_pass=True good_recall=1.0 weak_recall=0.0 delta=1.0
- **nodegoat-synthetic**: fixture_pass=True good_recall=1.0 weak_recall=0.0 delta=1.0
- **django-vuln-synthetic**: fixture_pass=True good_recall=1.0 weak_recall=0.0 delta=1.0

