<!-- torii-commercial-scorecard -->

# Commercial product scorecard

_Generated: `2026-08-01T14:44:49Z` · **overall_est=8.5/10** (baseline 6.6) · commercial_ok=`True`_

Single commercial scorecard: golden path · buyer · public eval · install · ops · enterprise

Heuristic commercial score from hermetic surface fixtures — not a customer interview score. Cap 8.5 until live revenue proof.

## Trajectory

| Metric | Value |
|--------|------:|
| baseline overall | 6.6 |
| overall_est | **8.5** |
| lift | +1.9 |
| surfaces pass | 6/6 |

## Priority queue surfaces

| Surface | Target | Dim | Pass |
|---------|--------|-----|:----:|
| `golden_path` | 7.5 | commercial / simplicity path | yes |
| `buyer_narrative` | 8.0 | simplicity (narrative) | yes |
| `public_eval` | 8.5 | technical trust | yes |
| `install_ux` | install | install UX (dim 7) | yes |
| `ops` | ops | reliability/ops (dim 8) | yes |
| `enterprise` | enterprise | enterprise light (dim 9) | yes |

## Buyer artifacts

| Artifact | Present |
|----------|:-------:|
| `buyer_diagram` | True |
| `enterprise_privacy` | True |
| `golden_path_md` | True |
| `install_md` | True |
| `ops_dashboard` | True |
| `public_eval_md` | True |

## Refresh

```bash
python3 scripts/commercial_scorecard.py report
python3 scripts/commercial_scorecard.py fixture
python3 scripts/torii.py commercial -- status
```

Related: [GOLDEN-PATH](../GOLDEN-PATH.md) · [public-eval](public-eval/SCORECARD.md) · [ops](../ops/DASHBOARD.md) · [enterprise](../enterprise/)
