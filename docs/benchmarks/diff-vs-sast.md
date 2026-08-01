<!-- torii-diff-vs-sast -->

# Diff vs SAST / AI review — surface check

_Generated: `2026-08-01T20:27:55Z` · fixture_pass=`True`_

Merge authority vs scanner noise vs chatty AI review — labeled_tp=18 · good_recall=1.0 · weak_fp_proxy=0.0

## Checks

| Check | Pass |
|-------|:----:|
| `diff_md` | yes |
| `matrix_sast` | yes |
| `matrix_ai_review` | yes |
| `merge_authority` | yes |
| `path_evidence` | yes |
| `public_eval_link` | yes |
| `honesty_not_replace` | yes |
| `honesty_no_zero_fp` | yes |
| `labeled_metrics_table` | yes |
| `path_to_value` | yes |
| `landing_compare` | yes |
| `landing_links_diff` | yes |
| `product_links_diff` | yes |
| `readme_links_diff` | yes |
| `public_eval_artifact` | yes |
| `cites_labeled_tp` | yes |
| `public_eval_fresh_enough` | yes |

## Public-eval snapshot (linked evidence)

- labeled_tp: **18**
- good_recall_mean: **1.0**
- weak_recall_mean (FP proxy): **0.0**
- public_eval_ok: **True**

One-pager: [`docs/DIFF.md`](../DIFF.md) · Public eval: [`public-eval/SCORECARD.md`](public-eval/SCORECARD.md)

```bash
python3 scripts/diff_vs_sast.py fixture
python3 scripts/torii.py diff -- status
```
