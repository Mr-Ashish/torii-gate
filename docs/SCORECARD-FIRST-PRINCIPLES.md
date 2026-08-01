# Torii Gate — first-principles product scorecard

_Scored: `2026-08-01T18:29:14Z` · baseline overall **6.6** · commercial fixture **8.5** (cap) · buyer adoption lens._

**Lens:** Would a Platform / AppSec buyer install next week and require `torii/gate` without reading `docs/research/`?

Cap honest overall **≤8.0** until live revenue / paid pilot proof.

## Dimensions 1–12 (1–10)

| # | Dimension | Score | One-line evidence |
|---|-----------|------:|-------------------|
| 1 | Pain clarity | **9** | Merge authority story on PRODUCT/README. |
| 2 | ICP / buyer | **8.5** | ICP + PRICING.md open core. |
| 3 | JTBD / path-to-value | **8.5** | Own-repo quieter from **`.torii/runs/`** after pack install (not hub vault only). |
| 4 | Differentiation | **8.5** | Security merge authority vs chatbot. |
| 5 | Evidence / technical trust | **8.5** | Public eval 4/4 · cost p50 · Modal dogfood. |
| 6 | Moat / compound loops | **8** | L3 skill+memory+workflow (Advanced). |
| 7 | Install UX | **8.5** | Pack ships quieter_over_time + gate_certificate; INSTALL own-repo quieter path. |
| 8 | Ops / reliability | **8** | Fail-closed · cost vault · smoke. |
| 9 | Enterprise light | **7.5** | --tenant + privacy docs. |
| 10 | Pricing / packaging | **7** | docs/PRICING.md open core. |
| 11 | GTM / distribution | **7.5** | README/landing/pricing. |
| 12 | Simplicity / cognitive load | **7.5** | Day-1/Day-2/Advanced help. |

### Weighted overall

| Dim | w | Score | w×s |
|-----|--:|------:|----:|
| 1 | 0.06 | 9.0 | 0.54 |
| 2 | 0.06 | 8.5 | 0.51 |
| 3 | 0.12 | 8.5 | 1.02 |
| 4 | 0.07 | 8.5 | 0.60 |
| 5 | 0.10 | 8.5 | 0.85 |
| 6 | 0.07 | 8.0 | 0.56 |
| 7 | 0.11 | 8.5 | 0.94 |
| 8 | 0.09 | 8.0 | 0.72 |
| 9 | 0.08 | 7.5 | 0.60 |
| 10 | 0.06 | 7.0 | 0.42 |
| 11 | 0.06 | 7.5 | 0.45 |
| 12 | 0.12 | 7.5 | 0.90 |
| **Overall** | 1.00 | | **8.1** → **cap 8.0** (pre-revenue) |

**Reported overall:** **8.0** (weighted 8.1 capped). **Band:** **A- adoption-ready OSS** — path-to-value quieter on customer vault; still open on enterprise isolation hermetic + paid pilot.

## Ranked GAP list (max 10)

| Rank | Gap | Lifts | Effort | ROI | Status |
|-----:|-----|-------|--------|-----|--------|
| 1 | CLI cognitive-load collapse | #12 | S | 🔥 | **shipped** `2325be7` |
| 2 | Pricing / packaging product surface | #10 | S | 🔥 | **shipped** `7a5c0ca` |
| 3 | Own-repo quieter path after pack install | #3 · #7 | M | 🔥 | **shipped** `2db184f` |
| 4 | Enterprise isolation hermetic proof | #9 | S | med | next |
| 5 | Public eval freshness badge | #5 · #11 | XS | med | later |
| 6 | Required-check onboarding in GH Actions summary | #3 · #7 | S | med | later |
| 7 | Deployed landing | #11 | M | med | later |
| 8 | Paid pilot / revenue proof | #10 | L | high | later |
| 9 | Trust layer (SARIF) | #4 | L | low | vision |
| 10 | Avoid F185+ without customer win | #12 | — | — | standing rule |

## Refresh

```bash
python3 scripts/torii.py quieter -- fixture
python3 scripts/torii.py quieter -- status
python3 scripts/buyer_narrative_check.py fixture
```

Related: [`QUIETER.md`](QUIETER.md) · [`PRICING.md`](PRICING.md) · [`INSTALL.md`](INSTALL.md)
