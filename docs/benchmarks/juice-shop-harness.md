# Juice Shop harness (F76)

Dogfood Torii Gate against **Juice Shop challenge themes** using a **license-safe synthetic** mini-app — not a fork of [OWASP Juice Shop](https://github.com/juice-shop/juice-shop).

## Layout

```text
demo/juice-shop-synthetic/          # original Express-style vulns (do not deploy)
docs/benchmarks/cases/juice-shop-synthetic.json
docs/benchmarks/fixtures/juice-shop-synthetic-{good,weak}-review.md
docs/benchmarks/juice-shop/INDEX.md
scripts/bench_corpus.py             # multi-pack: insecure-demo + juice-shop-synthetic
```

## Themes → cases

| id | Theme | CWE |
|----|--------|-----|
| js-sqli | SQL injection in product search | CWE-89 |
| js-xss | Reflected XSS in feedback | CWE-79 |
| js-cmdi | `child_process.exec` ping | CWE-78 |
| js-secret | Hardcoded JWT / API key | CWE-798 |
| js-authz | IDOR on basket | CWE-639 |

## Offline

```bash
# Single pack
python3 scripts/bench_corpus.py fixture --pack juice-shop-synthetic

# All packs (insecure-demo + juice-shop-synthetic)
python3 scripts/bench_corpus.py all
# → .torii-out/bench-f76/corpus-metrics.json  all_pass=1

# Taint prefilter on synthetic routes
python3 scripts/bench_corpus.py taint --pack juice-shop-synthetic

# F70 scorer direct
python3 scripts/bench_security_gate.py score \
  --review docs/benchmarks/fixtures/juice-shop-synthetic-good-review.md \
  --cases docs/benchmarks/cases/juice-shop-synthetic.json --json
```

## Live path

1. Open a PR touching `demo/juice-shop-synthetic/routes.js` (or review that tree in workspace).
2. `@torii review this pr` with security pack; POST_COMMENT as needed.
3. Prefer path-evidenced findings matching the five required cases.
4. Archive traces under `docs/benchmarks/traces/` (F73 vault).

## Non-goals

- Full Juice Shop CTF automation
- Vendoring the real Juice Shop monorepo
- Live exploit against a deployed shop
