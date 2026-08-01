<!-- torii-quieter-over-time -->

# Quieter-over-time (own-repo required check)

_Generated: `2026-08-01T18:10:32Z` · feature **QUIETER** · quieter_ok=`True`_

**One-liner:** Own-repo required check torii/gate + quieter-over-time dogfood chart

**Required check:** `torii/gate`

Buyer path:

```text
install pack → OPENROUTER_API_KEY → branch protection requires torii/gate
    → @torii review → path-evidenced signal → next PR quieter
```

Buyer doc: [`docs/QUIETER.md`](../QUIETER.md) · Golden path: [`GOLDEN-PATH.md`](../GOLDEN-PATH.md)

## Own-repo required-check readiness

| Metric | Value |
|--------|------:|
| checks ok | 10/10 |
| own_repo_ok | True |

| Check | Pass |
|-------|:----:|
| `golden_path_doc` | yes |
| `gate_doc` | yes |
| `quieter_buyer_doc` | yes |
| `install_script` | yes |
| `pack_caller` | yes |
| `gate_status_script` | yes |
| `gate_certificate_script` | yes |
| `smoke_script` | yes |
| `branch_protection_named` | yes |
| `required_context_torii_gate` | yes |

## Dogfood trajectory (early → late)

Quieter means: more path evidence + tool use + certificates; fewer weak APPROVEs.

| Window | n | path_ev mean | tool_use rate | cert rate | weak APPROVE | quiet_score |
|--------|--:|-------------:|--------------:|----------:|-------------:|------------:|
| early | 38 | 0.8938 | 0.8421 | 0.0 | 0.0 | 0.7154 |
| late | 39 | 1.0 | 0.7949 | 0.6923 | 0.0 | 0.8769 |
| all | 77 | 0.9757 | 0.8182 | 0.3506 | 0.0 | 0.8071 |

**delta quiet_score (late − early):** `0.1615` · **getting_quieter:** `True`

## Agent tool-use quality (tools-as-code)

| Metric | Value |
|--------|------:|
| measured runs | 72 |
| tool_use_rate | 0.875 |
| mean turns | 5.58 |
| zero-tool runs | 9 |
| quality_ok | True |

## Cost / time (all dogfood)

| Metric | Value |
|--------|------:|
| cost/PR mean USD | 0.017 (n=34) |
| time-to-signal mean s | 101.7 |

## Recent dogfood rows

| trace | repo | pr | verdict | tools | path_ev | cert | weak_appr |
|-------|------|---:|---------|------:|--------:|:----:|:---------:|
| `20260801-1636-pytorch-pytorch-PR191840-modal-rea` | pytorch/pytorch | 191840 | APPROVE | 6 | 1.0 | yes |  |
| `20260801-1642-pytorch-pytorch-PR191840-modal-ent` | pytorch/pytorch | 191840 | APPROVE | 3 | 1.0 | yes |  |
| `20260801-1649-pytorch-pytorch-PR191840-modal-com` | pytorch/pytorch | 191840 | APPROVE | 5 | 1.0 | yes |  |
| `20260801-1654-pytorch-pytorch-PR191840-modal-bra` | pytorch/pytorch | 191840 | REQUEST_CHANGES | 9 | 1.0 | yes |  |
| `20260801-1700-pytorch-pytorch-PR191840-modal-ins` | pytorch/pytorch | 191840 | REQUEST_CHANGES | 8 | 1.0 | yes |  |
| `20260801-1706-pytorch-pytorch-PR191840-modal-day` | pytorch/pytorch | 191840 | APPROVE | 4 | 1.0 | yes |  |
| `20260801-1712-pytorch-pytorch-PR191840-modal-gat` | pytorch/pytorch | 191840 | APPROVE | 4 | 1.0 | yes |  |
| `20260801-1719-pytorch-pytorch-PR191840-modal-cer` | pytorch/pytorch | 191840 | APPROVE | 9 | 1.0 | yes |  |
| `20260801-1728-pytorch-pytorch-PR191840-modal-sta` | pytorch/pytorch | 191840 | APPROVE | 7 | 1.0 | yes |  |
| `20260801-1743-pytorch-pytorch-PR191840-modal-ent` | pytorch/pytorch | 191840 | APPROVE | 5 | 1.0 | yes |  |
| `20260801-1753-pytorch-pytorch-PR191840-modal-gtm` | pytorch/pytorch | 191840 | APPROVE | 4 | 1.0 | yes |  |
| `20260801-1800-pytorch-pytorch-PR191840-modal-gol` | pytorch/pytorch | 191840 | APPROVE | 5 | 1.0 | yes |  |

## Refresh

```bash
python3 scripts/quieter_over_time.py report
python3 scripts/torii.py quieter -- status
```
