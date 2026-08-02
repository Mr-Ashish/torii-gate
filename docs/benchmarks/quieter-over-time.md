<!-- torii-quieter-over-time -->

# Quieter-over-time (own-repo required check)

_Generated: `2026-08-02T04:37:25Z` · feature **QUIETER** · quieter_ok=`True`_

**One-liner:** Own-repo required check torii/gate + quieter chart from .torii/runs (customer) and/or hub dogfood vault

**Required check:** `torii/gate`

Buyer path:

```text
install pack → OPENROUTER_API_KEY → branch protection requires torii/gate
    → @torii review → runs land in .torii/runs/ → quieter chart (this file)
```

Buyer doc: [`docs/QUIETER.md`](../QUIETER.md) · Golden path: [`GOLDEN-PATH.md`](../GOLDEN-PATH.md)

## Vaults (customer + hub)

| Metric | Value |
|--------|------:|
| local `.torii/runs` rows | 5 |
| hub dogfood rows | 113 |
| total rows | 116 |

Customer repos measure quieter from **`.torii/runs/`** after pack install — no hub clone required.

## Own-repo required-check readiness

| Metric | Value |
|--------|------:|
| checks ok | 14/14 |
| own_repo_ok | True |
| pack_surface_ok | True |
| hub_docs_ok | True |

| Check | Pass |
|-------|:----:|
| `golden_path_doc` | yes |
| `gate_doc` | yes |
| `quieter_buyer_doc` | yes |
| `install_script` | yes |
| `pack_caller` | yes |
| `gate_status_script` | yes |
| `gate_certificate_script` | yes |
| `quieter_script` | yes |
| `torii_cli` | yes |
| `smoke_script` | yes |
| `local_runs_parent` | yes |
| `branch_protection_named` | yes |
| `required_context_torii_gate` | yes |
| `customer_path_documented` | yes |

## Trajectory (early → late)

Quieter means: more path evidence + tool use + certificates; fewer weak APPROVEs.

| Window | n | path_ev mean | tool_use rate | cert rate | weak APPROVE | quiet_score |
|--------|--:|-------------:|--------------:|----------:|-------------:|------------:|
| early | 58 | 0.9346 | 0.7586 | 0.1034 | 0.0 | 0.7254 |
| late | 58 | 1.0 | 0.4483 | 0.3793 | 0.0 | 0.7103 |
| all | 116 | 0.9757 | 0.6034 | 0.2414 | 0.0 | 0.7208 |

**delta quiet_score (late − early):** `-0.0151` · **getting_quieter:** `True`

## Agent tool-use quality (tools-as-code)

| Metric | Value |
|--------|------:|
| measured runs | 79 |
| tool_use_rate | 0.8861 |
| mean turns | 6.03 |
| zero-tool runs | 9 |
| quality_ok | True |

## Cost / time (all rows)

| Metric | Value |
|--------|------:|
| cost/PR mean USD | 0.0168 (n=35) |
| time-to-signal mean s | 173.4 |

## Recent rows

| trace | vault | repo | pr | verdict | tools | path_ev | cert | weak_appr |
|-------|-------|------|---:|---------|------:|--------:|:----:|:---------:|
| `20260802-0105-pytorch-pytorch-PR191854-m` | hub_traces | pytorch/pytorch | 191854 | UNKNOWN | None | None |  |  |
| `20260802-0121-pytorch-pytorch-PR191851-m` | hub_traces | pytorch/pytorch | 191851 | UNKNOWN | None | None |  |  |
| `20260802-0139-pytorch-pytorch-PR191853-m` | hub_traces | pytorch/pytorch | 191853 | UNKNOWN | None | None |  |  |
| `20260802-0154-pytorch-pytorch-PR191852-m` | hub_traces | pytorch/pytorch | 191852 | UNKNOWN | None | None |  |  |
| `20260802-0211-pytorch-pytorch-PR191854-m` | hub_traces | pytorch/pytorch | 191854 | UNKNOWN | None | None |  |  |
| `20260802-0227-pytorch-pytorch-PR191851-m` | hub_traces | pytorch/pytorch | 191851 | UNKNOWN | None | None |  |  |
| `20260802-0249-pytorch-pytorch-PR191852-m` | hub_traces | pytorch/pytorch | 191852 | UNKNOWN | None | None |  |  |
| `LANDING_PARTNER_CTA-20260802T034847Z` | hub_traces | pytorch/pytorch | 191854 | APPROVE | 10 | None |  |  |
| `PARTNER_WEEK1-20260802T041230Z` | hub_traces | pytorch/pytorch | 191854 | APPROVE | 15 | None |  |  |
| `f176-free-rider-revive-gate` | hub_traces | pytorch/pytorch | 191836 | UNKNOWN | None | None |  |  |
| `merge-diff-vs-sast-20260802T0306Z` | hub_traces | pytorch/pytorch | 191852 | APPROVE | 9 | None |  |  |
| `pilot-proof-gtm-apply-20260802T0326Z` | hub_traces | pytorch/pytorch | 191854 | APPROVE | 10 | None |  |  |

## Refresh

```bash
python3 scripts/quieter_over_time.py report
python3 scripts/torii.py quieter -- status
# customer pack also writes .torii/quieter-over-time.md
```
