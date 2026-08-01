# Torii Gate — first-principles product scorecard

_Scored: `2026-08-01T18:12Z` · baseline overall **6.6** · commercial fixture **8.5** (cap) · this sheet is **buyer adoption**, not research harness readiness._

**Lens:** Would a Platform / AppSec buyer install this next week and make `torii/gate` a required check — without reading `docs/research/`?

Heuristic only (no customer interviews). Cap honest overall **≤8.0** until live revenue / paid pilot proof.

## Dimensions 1–12 (1–10)

| # | Dimension | Score | One-line evidence |
|---|-----------|------:|-------------------|
| 1 | Pain clarity | **9** | PRODUCT/README: AI PR volume + unguarded merges; “nothing ships without crossing the gate.” |
| 2 | ICP / buyer | **8** | Platform / AppSec / eng-lead table in PRODUCT; non-ICP explicit. Pricing path still draft (Hub71). |
| 3 | JTBD / path-to-value | **7.5** | Install → require `torii/gate` → quieter chart (`docs/QUIETER.md`, dogfood n=77, getting_quieter). Chart still hub-vault centric for customers. |
| 4 | Differentiation | **8.5** | Merge authority + maker/checker + compound memory vs “AI code-review chatbot.” |
| 5 | Evidence / technical trust | **8.5** | Public labeled eval 4/4 packs recall=1.0 · cost p50 ~$0.014 · Modal pytorch dogfood vault. |
| 6 | Moat / compound loops | **8** | Skill L3 + memory L3 + workflow L3 + hub-archival/GEPA measured — real, but sold as Advanced. |
| 7 | Install UX | **8** | `install-torii.sh` · `--minimal` · `--tenant` · INSTALL 5-min · doctor/status one CLI. |
| 8 | Ops / reliability | **8** | Fail-closed tool-turns · smoke CI · cost/PR vault · `ops -- status` · RELIABILITY.md. |
| 9 | Enterprise light | **7.5** | Org isolation docs + `--tenant` stamp + federation privacy (themes/hashes). Not a SaaS control plane; isolation is light. |
| 10 | Pricing / packaging | **4** | Only draft seats/ACV in `docs/hub71/ACCESS-APPLY.md`. No product SKU surface. |
| 11 | GTM / distribution | **7** | Strong README + landing + PRODUCT; open-source MIT; pre-revenue; no deployed marketing site. |
| 12 | Simplicity / cognitive load | **6.5** | Buyer surfaces hide F-IDs (buyer fixture 28/28) but CLI help lists **19** peer groups flat — research harness feel. |

### Weighted overall

Weights emphasize path-to-value + simplicity + install (adoption), not research depth:

| Dim | w | Score | w×s |
|-----|--:|------:|----:|
| 1 Pain | 0.06 | 9.0 | 0.54 |
| 2 ICP | 0.06 | 8.0 | 0.48 |
| 3 JTBD | 0.12 | 7.5 | 0.90 |
| 4 Diff | 0.07 | 8.5 | 0.60 |
| 5 Evidence | 0.10 | 8.5 | 0.85 |
| 6 Moat | 0.07 | 8.0 | 0.56 |
| 7 Install | 0.11 | 8.0 | 0.88 |
| 8 Ops | 0.09 | 8.0 | 0.72 |
| 9 Enterprise | 0.08 | 7.5 | 0.60 |
| 10 Pricing | 0.06 | 4.0 | 0.24 |
| 11 GTM | 0.06 | 7.0 | 0.42 |
| 12 Simplicity | 0.12 | 6.5 | 0.78 |
| **Overall** | 1.00 | | **7.6** |

**Band:** **B+ adoption-ready open source** — strong gate product, still reads like a research-complete hub more than a 5-command buy.

Commercial fixture **8.5** measures surface completeness; this sheet measures **buyer cognitive load + commercial packaging**. Do not average blindly — ship gaps below.

## Ranked GAP list (max 10 · crucial missing only)

| Rank | Gap | Lifts | Effort | ROI | Status |
|-----:|-----|-------|--------|-----|--------|
| 1 | **CLI cognitive-load collapse** — tier Day-1 / Day-2 / Advanced help; strip F-IDs from primary help | #12 · #3 · #7 | S | 🔥 | **shipped**  |
| 2 | **Pricing / packaging product surface** — public Starter/Team/Business (or “open core + support”) without Hub71 archaeology | #10 · #11 · #2 | S | 🔥 | next |
| 3 | **Own-repo quieter path after pack install** — customer vault quieter without hub dogfood archaeology | #3 · #7 | M | 🔥 | next |
| 4 | **Enterprise isolation hermetic proof** — fixture: tenant A memory never injects into tenant B prompt | #9 | S | med | next |
| 5 | **Public eval freshness badge** — scored_at age + model pin on landing/README | #5 · #11 | XS | med | later |
| 6 | **Required-check onboarding copy in GH Actions summary** — first-run “add torii/gate” checklist | #3 · #7 | S | med | later |
| 7 | **Deployed landing** (not only `docs/brand/landing.html` in repo) | #11 | M | med | later |
| 8 | **Paid pilot / revenue proof** (unblocks commercial cap >8.5) | #10 · commercial | L | high | later |
| 9 | **Trust layer (Torii Trust / SARIF)** roadmap item as optional path | #4 · #6 | L | low now | vision |
| 10 | Avoid F185+ compound loops without customer win | #12 | — | — | standing rule |

## What we will not do this fire

- New GEPA / hub-archival / re-prompt compound layers (F185+).
- Scorecard-only churn without shipping a gap close.
- SaaS multi-tenant control plane.

## Refresh

```bash
# re-read surfaces then edit this file
python3 scripts/torii.py status --text
python3 scripts/torii.py commercial -- status
python3 scripts/torii.py quieter -- status
python3 scripts/torii.py enterprise -- status
python3 scripts/torii.py public-eval -- status
```

Related: [`docs/benchmarks/commercial-scorecard.md`](benchmarks/commercial-scorecard.md) · [`PRODUCT.md`](../PRODUCT.md) · [`docs/GOLDEN-PATH.md`](GOLDEN-PATH.md)
