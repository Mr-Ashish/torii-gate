# Juice Shop harness (stub)

Lightweight plan to dogfood Torii Gate against [OWASP Juice Shop](https://github.com/juice-shop/juice-shop) without building a full ASPM product.

## Goal

Measure whether Torii Gate surfaces **path-evidenced** security findings on realistic vulnerable app PRs, with low false-positive rate via `.torii/` memory.

## Non-goals (v1)

- Full CTF solve automation
- Live exploit execution against deployed Juice Shop
- Replacing SAST/DAST pipelines

## Proposed layout (not implemented)

```text
docs/benchmarks/juice-shop/
  cases.json          # id, path globs, expected CWE/tags, severity floor
  fixtures/           # optional minimal diffs (synthetic, license-safe)
scripts/bench-juice-shop-gate.py   # offline: score review.md vs cases.json
```

## Case sketch

| id | Theme | Expected signal |
|----|--------|-----------------|
| js-sqli | SQL/NoSQL injection in search/login | REQUEST CHANGES or Security audit concern |
| js-xss | Reflected/stored XSS | path + payload shape |
| js-authz | Broken access control | authz fail-open / IDOR |
| js-secret | Hardcoded token / weak crypto | secrets / crypto lens |

## Offline path (today) — F70 labeled bench

In-repo ground truth + dual-pass critic + TP signature compound memory:

```bash
# Offline e2e: good vs weak review fixtures scored against demo/insecure cases
python3 scripts/bench_security_gate.py fixture
# → .torii-out/bench-f70/bench-metrics.json (recall, delta_recall, fixture_pass)
# → tp-signatures.json promoted from confirmed TPs

python3 scripts/bench_security_gate.py score \
  --review docs/benchmarks/fixtures/insecure-demo-good-review.md \
  --cases docs/benchmarks/cases/insecure-demo.json --json

./scripts/smoke-torii-gate.sh          # gate decision + fixture integrity
# Live PR path:
# open PR touching demo/insecure/app.py → @torii review this pr
# Optional live agent bench (needs OPENROUTER_API_KEY):
# python3 scripts/bench_security_gate.py live --timeout 180
```

Cases pack: `docs/benchmarks/cases/insecure-demo.json` (SQLi, pickle, cmdi, secrets).

## Live path (later)

1. Fork or vendor a **pinned** Juice Shop commit (record SHA + license).
2. Open synthetic PRs that re-introduce one vuln class at a time (or review historical fix PRs reversed).
3. Run Torii Gate; store redacted review under `docs/showcase/juice-shop-<case>/`.
4. Score: TP if expected theme appears with path evidence; FP if invented vulns or wrong file.

## Success metrics

| Metric | Target (draft) |
|--------|----------------|
| Time-to-first-signal | &lt; review budget (see `TORII_MAX_COST_USD`) |
| TP on seeded cases | ≥ 3/4 themes on first pass |
| Invented-vuln rate | 0 on fixture-only smoke; track on live |

## Status

**F70 scorer live** for `demo/insecure` labeled cases (`scripts/bench_security_gate.py`).
Juice Shop vendor checkout still deferred; use insecure-demo pack as the measured e2e path.
