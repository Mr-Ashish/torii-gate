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

## Offline path (today)

Until cases land, use the in-repo dogfood:

```bash
./scripts/smoke-torii-gate.sh          # gate decision + fixture integrity
# Live PR path:
# open PR touching demo/insecure/app.py → @torii review this pr
```

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

**Stub only** — no Juice Shop checkout or scorer in-tree yet. Ship gate smoke + `demo/insecure` first.
