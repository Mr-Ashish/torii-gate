<!-- torii-quieter-over-time -->

# Quieter-over-time (own-repo required check)

_Generated: `2026-08-02T01:04:33Z` · feature **QUIETER** · quieter_ok=`True`_

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
| local `.torii/runs` rows | 3 |
| hub dogfood rows | 102 |
| total rows | 103 |

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
| early | 51 | 0.8938 | 0.7255 | 0.0196 | 0.0 | 0.6844 |
| late | 52 | 1.0 | 0.5192 | 0.5192 | 0.0 | 0.7596 |
| all | 103 | 0.9757 | 0.6214 | 0.2718 | 0.0 | 0.7323 |

**delta quiet_score (late − early):** `0.0752` · **getting_quieter:** `True`

## Agent tool-use quality (tools-as-code)

| Metric | Value |
|--------|------:|
| measured runs | 73 |
| tool_use_rate | 0.8767 |
| mean turns | 5.58 |
| zero-tool runs | 9 |
| quality_ok | True |

## Cost / time (all rows)

| Metric | Value |
|--------|------:|
| cost/PR mean USD | 0.0168 (n=35) |
| time-to-signal mean s | 102.8 |

## Recent rows

| trace | vault | repo | pr | verdict | tools | path_ev | cert | weak_appr |
|-------|-------|------|---:|---------|------:|--------:|:----:|:---------:|
| `20260801-2042-pytorch-pytorch-PR191842-m` | hub_traces | pytorch/pytorch | 191840 | UNKNOWN | None | None |  |  |
| `20260801-2107-pytorch-pytorch-PR191840-m` | hub_traces | pytorch/pytorch | 191840 | UNKNOWN | None | None |  |  |
| `20260801-2130-pytorch-pytorch-PR191840-m` | hub_traces | pytorch/pytorch | 191840 | UNKNOWN | None | None |  |  |
| `20260801-2156-pytorch-pytorch-PR191840-m` | hub_traces | pytorch/pytorch | 191840 | UNKNOWN | None | None |  |  |
| `20260801-2221-pytorch-pytorch-PR191840-m` | hub_traces | pytorch/pytorch | 191840 | UNKNOWN | None | None |  |  |
| `20260801-2238-pytorch-pytorch-PR191844-m` | hub_traces | pytorch/pytorch | 191844 | UNKNOWN | None | None |  |  |
| `20260801-2254-pytorch-pytorch-PR191840-m` | hub_traces | pytorch/pytorch | 191840 | UNKNOWN | None | None |  |  |
| `20260801-2313-pytorch-pytorch-PR191840-m` | hub_traces | pytorch/pytorch | 191840 | UNKNOWN | None | None |  |  |
| `20260801-2342-pytorch-pytorch-PR191842-m` | hub_traces | pytorch/pytorch | 191840 | UNKNOWN | None | None |  |  |
| `20260802-0019-pytorch-pytorch-PR191840-m` | hub_traces | pytorch/pytorch | 191840 | UNKNOWN | None | None |  |  |
| `20260802-0042-pytorch-pytorch-PR191852-m` | hub_traces | pytorch/pytorch | 191852 | UNKNOWN | None | None |  |  |
| `f176-free-rider-revive-gate` | hub_traces | pytorch/pytorch | 191836 | UNKNOWN | None | None |  |  |

## Refresh

```bash
python3 scripts/quieter_over_time.py report
python3 scripts/torii.py quieter -- status
# customer pack also writes .torii/quieter-over-time.md
```
