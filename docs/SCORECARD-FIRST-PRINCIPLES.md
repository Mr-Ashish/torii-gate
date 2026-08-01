# Torii Gate — first-principles product scorecard

_Scored: `2026-08-01T18:36:35Z` · baseline **6.6** · commercial fixture **8.5** · buyer adoption lens · cap **8.0** until paid pilot._

## Dimensions 1–12 (1–10)

| # | Dimension | Score | One-line evidence |
|---|-----------|------:|-------------------|
| 1 | Pain clarity | **9** | Merge authority on PRODUCT/README. |
| 2 | ICP / buyer | **8.5** | ICP + PRICING.md open core. |
| 3 | JTBD / path-to-value | **8.5** | Own-repo quieter from `.torii/runs/`. |
| 4 | Differentiation | **8.5** | Security merge authority vs chatbot. |
| 5 | Evidence / technical trust | **8.5** | Public eval + cost vault + Modal dogfood. |
| 6 | Moat / compound loops | **8** | L3 skill+memory+workflow (Advanced). |
| 7 | Install UX | **8.5** | Pack ships quieter/gate scripts; Day-1 help. |
| 8 | Ops / reliability | **8** | Fail-closed · cost · smoke. |
| 9 | Enterprise light | **8.5** | Hermetic cross-tenant inject proof + federation sanitize. |
| 10 | Pricing / packaging | **7** | docs/PRICING.md open core · pre-revenue. |
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
| 9 | 0.08 | 8.5 | 0.68 |
| 10 | 0.06 | 7.0 | 0.42 |
| 11 | 0.06 | 7.5 | 0.45 |
| 12 | 0.12 | 7.5 | 0.90 |
| **Overall** | 1.00 | | **8.2** → **cap 8.0** |

**Reported overall:** **8.0**. **Band:** **A- adoption-ready OSS**.

## Ranked GAP list

| Rank | Gap | Lifts | Status |
|-----:|-----|-------|--------|
| 1 | CLI cognitive-load collapse | #12 | **shipped** |
| 2 | Pricing / packaging | #10 | **shipped** |
| 3 | Own-repo quieter path | #3 · #7 | **shipped** |
| 4 | Enterprise isolation hermetic proof | #9 | **shipped** `054055a` |
| 5 | Public eval freshness badge | #5 · #11 | next |
| 6 | Required-check onboarding in GH Actions summary | #3 · #7 | later |
| 7 | Deployed landing | #11 | later |
| 8 | Paid pilot / revenue proof | #10 | later |
| 9 | Trust layer (SARIF) | #4 | vision |
| 10 | Avoid F185+ without customer win | #12 | standing |

## Refresh

```bash
python3 scripts/enterprise_surface.py fixture
python3 scripts/torii.py quieter -- fixture
python3 scripts/torii.py commercial -- status
```
