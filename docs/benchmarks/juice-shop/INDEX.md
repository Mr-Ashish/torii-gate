# F76 multi-corpus security bench INDEX

Updated: `2026-08-01T00:39:45Z`

License-safe packs for offline recall/precision measurement.
Juice Shop pack is **synthetic original code** (themes only — not a fork).

| Pack | Lang | Cases | Paths OK | Source |
|------|------|------:|:--------:|--------|
| `insecure-demo` | py | 4 | yes | `demo/insecure` |
| `juice-shop-synthetic` | js | 5 | yes | `demo/juice-shop-synthetic` |

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

