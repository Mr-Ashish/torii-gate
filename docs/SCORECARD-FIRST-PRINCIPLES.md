# Torii Gate — first-principles product scorecard

_Scored: `2026-08-01T18:51:12Z` · commercial **8.5** · buyer adoption · overall **8.0** (cap until paid pilot)._

## Dims (1–12) highlights

| # | Dim | Score | Note |
|---|-----|------:|------|
| 3 | JTBD | **8.5** | Gate onboarding in Actions summary + own-repo quieter |
| 5 | Evidence | **9** | Public eval freshness |
| 7 | Install | **8.5** | First-run job summary checklist |
| 9 | Enterprise | **8.5** | Isolation proof |
| 10 | Pricing | **7** | Open core |
| 12 | Simplicity | **7.5** | Day-1 help tiers |

**Overall:** **8.0** (capped).

## Gaps

| Rank | Gap | Status |
|-----:|-----|--------|
| 1–5 | help · pricing · quieter · isolation · public-eval freshness | **shipped** |
| 6 | Required-check onboarding in GH Actions summary | **shipped** `a1365a0` |
| 7 | Deployed landing | next |
| 8 | Paid pilot | later |
| 9 | SARIF Trust layer | vision |
| 10 | No F185+ without customer win | standing |

```bash
python3 scripts/ops_footer.py fixture
python3 scripts/ops_footer.py gate-onboarding
```
