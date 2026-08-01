# Torii Gate — first-principles product scorecard

_Scored: `2026-08-01T18:43:55Z` · baseline **6.6** · commercial **8.5** · buyer adoption · cap **8.0** until paid pilot._

## Dimensions 1–12

| # | Dimension | Score | Evidence |
|---|-----------|------:|----------|
| 1 | Pain clarity | **9** | Merge authority story |
| 2 | ICP / buyer | **8.5** | ICP + PRICING |
| 3 | JTBD | **8.5** | Own-repo quieter `.torii/runs` |
| 4 | Differentiation | **8.5** | Gate vs chatbot |
| 5 | Evidence / technical trust | **9** | Public eval + **freshness badge** (seed/model/age) |
| 6 | Moat | **8** | L3 compound loops |
| 7 | Install UX | **8.5** | Pack quieter scripts |
| 8 | Ops | **8** | Fail-closed · cost |
| 9 | Enterprise | **8.5** | Hermetic isolation proof |
| 10 | Pricing | **7** | Open core PRICING.md |
| 11 | GTM | **8** | Landing freshness + pricing |
| 12 | Simplicity | **7.5** | Day-1/2/Advanced help |

### Weighted overall → **8.0** (cap; raw ~8.3)

## Ranked gaps

| Rank | Gap | Status |
|-----:|-----|--------|
| 1–4 | help collapse · pricing · own-repo quieter · isolation | **shipped** |
| 5 | Public eval freshness badge | **shipped** `b90e724` |
| 6 | Required-check onboarding in GH Actions summary | next |
| 7 | Deployed landing | later |
| 8 | Paid pilot | later |
| 9 | Trust layer SARIF | vision |
| 10 | No F185+ without customer win | standing |

```bash
python3 scripts/public_eval.py fixture
python3 scripts/public_eval.py status
```
