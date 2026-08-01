# Torii Gate — first-principles product scorecard

_Scored: `2026-08-01T20:27:56Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

Adoption lens (buyers, not research harness). Evidence from PRODUCT/README/fixtures/e2e/traces.

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.5 | PRODUCT: security merge authority · tagline · ICP table |
| 2 | Diff vs SAST/chat bots | **8.2** | **DIFF.md** + labeled public-eval (tp=18 · good=1.0 · weak=0.0) · landing compare |
| 3 | JTBD (quieter merge gate) | 8.5 | quieter_ok · getting_quieter · pilot readiness 8/8 |
| 4 | Agent tool quality | 8.0 | tool_use_rate=0.875 · model_alias → v4-pro |
| 5 | Memory / compound | 8.0 | memory L3 · hub-archival loop_ok |
| 6 | Self-evolution | 7.8 | Day-2 JSON status · dual_gate_safe |
| 7 | Install UX | 8.5 | 5-min INSTALL · `--minimal` |
| 8 | Ops / reliability | 8.5 | fail_closed · smoke_ci · cost vault |
| 9 | Enterprise light | 8.0 | isolation_ok · `--tenant` |
| 10 | Pricing / packaging | 8.0 | open core SKUs · no fake ARR |
| 11 | GTM / distribution | 7.5 | Pages landing · PILOT · DIFF one-pager |
| 12 | Simplicity / cognitive load | 7.6 | Day-1/2/Advanced help · status one-screen |

**Weighted overall (product):** ~**8.1** (still **cap 8.0** until paid pilot) · commercial **8.5**.  
**Band:** strong packaging · differentiation documented · not revenue-proven.

## This fire

**DIFF_VS_SAST:** `docs/DIFF.md` buyer one-pager · `diff_vs_sast.py` fixture linked to public-eval · Day-2 CLI `diff` · landing/PRODUCT/README · status row.

## Ranked remaining gaps

| Rank | Gap | Dim | Status |
|-----:|-----|-----|--------|
| 1 | First design partner / paid pilot close | 11 | open (human GTM) |
| 2 | Live customer quieter vault | 3 | open (partner install) |
| 3 | Diff-vs-SAST one-pager with labeled bench | 2 | **shipped** |
| 4 | Collapse PRODUCT advanced F-stack on landing | 12 | partial |
| 5 | Self-evolve day-2 without F-IDs | 6 | shipped |
| 6 | Public eval age &lt;72h | trust | standing |
| 7 | No F185+ without customer win | all | standing |
| 8 | Required-check short video | 7/11 | open |
| 9 | Billing live | 10/11 | deferred |
| 10 | Enterprise Plane / SSO | 9 | deferred |

```bash
python3 scripts/torii.py diff -- status
python3 scripts/diff_vs_sast.py fixture
```
