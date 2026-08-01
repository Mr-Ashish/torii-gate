# Torii Gate — first-principles product scorecard

_Scored: `2026-08-01T18:20:55Z` · baseline overall **6.6** · commercial fixture **8.5** (cap) · this sheet is **buyer adoption**, not research harness readiness._

**Lens:** Would a Platform / AppSec buyer install this next week and make `torii/gate` a required check — without reading `docs/research/`?

Heuristic only (no customer interviews). Cap honest overall **≤8.0** until live revenue / paid pilot proof.

## Dimensions 1–12 (1–10)

| # | Dimension | Score | One-line evidence |
|---|-----------|------:|-------------------|
| 1 | Pain clarity | **9** | PRODUCT/README: AI PR volume + unguarded merges; “nothing ships without crossing the gate.” |
| 2 | ICP / buyer | **8.5** | ICP table + **PRICING.md** open-core path (no Hub71 required). |
| 3 | JTBD / path-to-value | **7.5** | Install → require `torii/gate` → quieter chart. Chart still hub-vault centric for customers. |
| 4 | Differentiation | **8.5** | Merge authority + maker/checker + compound memory vs “AI code-review chatbot.” |
| 5 | Evidence / technical trust | **8.5** | Public labeled eval 4/4 packs · cost p50 ~$0.014 · Modal pytorch dogfood. |
| 6 | Moat / compound loops | **8** | Skill L3 + memory L3 + workflow L3 measured — sold as Advanced. |
| 7 | Install UX | **8** | `install-torii.sh` · `--minimal` · `--tenant` · Day-1 CLI tier. |
| 8 | Ops / reliability | **8** | Fail-closed tool-turns · smoke CI · cost/PR vault · `ops -- status`. |
| 9 | Enterprise light | **7.5** | Org isolation docs + `--tenant` + federation privacy. Not SaaS control plane. |
| 10 | Pricing / packaging | **7** | **docs/PRICING.md** open core · Team/Business/Enterprise indicative · pre-revenue honest · linked README/landing/PRODUCT. |
| 11 | GTM / distribution | **7.5** | README + landing + pricing section; open-source MIT; still no live billing. |
| 12 | Simplicity / cognitive load | **7.5** | HELP_CLI_COLLAPSE: Day-1/Day-2/Advanced help; F-IDs stripped from primary. |

### Weighted overall

| Dim | w | Score | w×s |
|-----|--:|------:|----:|
| 1 Pain | 0.06 | 9.0 | 0.54 |
| 2 ICP | 0.06 | 8.5 | 0.51 |
| 3 JTBD | 0.12 | 7.5 | 0.90 |
| 4 Diff | 0.07 | 8.5 | 0.60 |
| 5 Evidence | 0.10 | 8.5 | 0.85 |
| 6 Moat | 0.07 | 8.0 | 0.56 |
| 7 Install | 0.11 | 8.0 | 0.88 |
| 8 Ops | 0.09 | 8.0 | 0.72 |
| 9 Enterprise | 0.08 | 7.5 | 0.60 |
| 10 Pricing | 0.06 | 7.0 | 0.42 |
| 11 GTM | 0.06 | 7.5 | 0.45 |
| 12 Simplicity | 0.12 | 7.5 | 0.90 |
| **Overall** | 1.00 | | **7.9** |

**Band:** **B+ / approaching A-** — packaging + help collapse shipped; still open on own-repo quieter path and paid pilot.

Commercial fixture **8.5** = surface completeness. This sheet = **buyer packaging + cognitive load**.

## Ranked GAP list (max 10 · crucial missing only)

| Rank | Gap | Lifts | Effort | ROI | Status |
|-----:|-----|-------|--------|-----|--------|
| 1 | CLI cognitive-load collapse | #12 · #3 · #7 | S | 🔥 | **shipped** `2325be7` |
| 2 | Pricing / packaging product surface | #10 · #11 · #2 | S | 🔥 | **shipped** `7a5c0ca` |
| 3 | **Own-repo quieter path after pack install** | #3 · #7 | M | 🔥 | next |
| 4 | Enterprise isolation hermetic proof | #9 | S | med | next |
| 5 | Public eval freshness badge | #5 · #11 | XS | med | later |
| 6 | Required-check onboarding in GH Actions summary | #3 · #7 | S | med | later |
| 7 | Deployed landing | #11 | M | med | later |
| 8 | Paid pilot / revenue proof (unblocks commercial cap >8.5) | #10 | L | high | later |
| 9 | Trust layer (SARIF) optional path | #4 · #6 | L | low now | vision |
| 10 | Avoid F185+ without customer win | #12 | — | — | standing rule |

## What we will not do this fire

- New GEPA / hub-archival / re-prompt compound layers (F185+).
- Fake customers or live Stripe until real.
- SaaS multi-tenant control plane.

## Refresh

```bash
python3 scripts/torii.py status --text
python3 scripts/torii.py commercial -- status
python3 scripts/buyer_narrative_check.py fixture
```

Related: [`docs/PRICING.md`](PRICING.md) · [`docs/benchmarks/commercial-scorecard.md`](benchmarks/commercial-scorecard.md) · [`PRODUCT.md`](../PRODUCT.md)
