# Torii Gate — first-principles product scorecard

_Scored: `2026-08-01T19:42:00Z` · commercial **8.5** · overall **8.0** (cap until paid pilot)._

Adoption lens (buyers, not research harness). Evidence from PRODUCT/README/fixtures/e2e/traces.

## Dims 1–12

| # | Dim | Score | One-line evidence |
|--:|-----|------:|-------------------|
| 1 | Value prop | 8.5 | PRODUCT: security merge authority · tagline · ICP table |
| 2 | Diff vs SAST/chat bots | 7.5 | Maker+checker · path evidence · gate cert reason codes |
| 3 | JTBD (quieter merge gate) | 8.5 | quieter_ok · getting_quieter · quiet_score≈0.77 · pilot readiness 8/8 |
| 4 | Agent tool quality | 8.0 | tool_use_rate=0.875 · n=72 · model_alias → v4-pro |
| 5 | Memory / compound | 8.0 | memory L3 · hub-archival loop_ok · federation themes-only |
| 6 | Self-evolution | 7.0 | dual-gate adopt · GEPA refine docs; F-stack still engineer-facing |
| 7 | Install UX | 8.5 | 5-min INSTALL · `--minimal` · job-summary require-check |
| 8 | Ops / reliability | 8.5 | fail_closed_safe_defaults · smoke_ci · cost vault |
| 9 | Enterprise light | 8.0 | isolation_ok · `--tenant` · privacy themes-only |
| 10 | Pricing / packaging | 8.0 | open core SKUs · PRICING.md · no fake ARR |
| 11 | GTM / distribution | 7.5 | Pages landing · PILOT apply · **pilot CLI readiness** (this fire) |
| 12 | Simplicity / cognitive load | 7.5 | Day-1/2/Advanced help · status one-screen · PRODUCT advanced below fold |

**Weighted overall (product):** ~**8.0** · commercial surfaces **8.5/10** (cap 8.5 until revenue proof).  
**Band:** strong packaging · ready for design partners · not yet revenue-proven.

## This fire

**PILOT_READINESS:** Day-2 `torii pilot` group · measured readiness (cost · quieter · certs · public-eval · golden path) · status shows readiness n/total · PILOT.md success-criteria table.

## Ranked remaining gaps (max 10 · implementable first)

| Rank | Gap | Dim | ROI | Effort | Status |
|-----:|-----|-----|-----|--------|--------|
| 1 | First design partner / paid pilot close | 11 | high | human GTM | open |
| 2 | Live customer quieter vault (not only hub dogfood) | 3 | high | partner install | open |
| 3 | Collapse PRODUCT advanced F-stack further on landing | 12 | med | docs | partial |
| 4 | Diff-vs-SAST one-pager with labeled bench | 2 | med | eval+docs | open |
| 5 | Self-evolve day-2 one-liner without F-IDs | 6 | med | docs/CLI | open |
| 6 | Public eval keep age &lt;72h on every fire | 4/trust | med | refresh | standing |
| 7 | Enterprise SSO / Plane (not v1) | 9 | low now | roadmap | deferred |
| 8 | Billing live (Stripe) | 10/11 | high after pilot | eng+GTM | deferred |
| 9 | No F185+ without customer win | all | standing | discipline | standing |
| 10 | Required-check adoption playbook short video | 7/11 | med | GTM | open |

```bash
python3 scripts/torii.py pilot -- readiness
python3 scripts/torii.py pilot -- fixture
python3 scripts/torii.py status --text
```
