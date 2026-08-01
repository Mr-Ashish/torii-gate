<!-- torii-quieter-over-time -->

# Quieter-over-time (own-repo required check)

_Generated: `2026-08-01T15:15:21Z` · feature **QUIETER** · quieter_ok=`True`_

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
| early | 26 | 0.8938 | 0.8077 | 0.0 | 0.0 | 0.7051 |
| late | 27 | 1.0 | 0.6667 | 0.1111 | 0.0 | 0.7222 |
| all | 53 | 0.9227 | 0.7358 | 0.0566 | 0.0 | 0.705 |

**delta quiet_score (late − early):** `0.0171` · **getting_quieter:** `True`

## Agent tool-use quality (tools-as-code)

| Metric | Value |
|--------|------:|
| measured runs | 48 |
| tool_use_rate | 0.8125 |
| mean turns | 5.58 |
| zero-tool runs | 9 |
| quality_ok | True |

## Cost / time (all dogfood)

| Metric | Value |
|--------|------:|
| cost/PR mean USD | 0.0164 (n=10) |
| time-to-signal mean s | 98.3 |

## Recent dogfood rows

| trace | repo | pr | verdict | tools | path_ev | cert | weak_appr |
|-------|------|---:|---------|------:|--------:|:----:|:---------:|
| `20260801-0455-pytorch-pytorch-PR191813-modal-f11` | pytorch/pytorch | 191813 | UNKNOWN | 4 | None |  |  |
| `20260801-0505-pytorch-pytorch-PR191813-modal-f11` | pytorch/pytorch | 191813 | REQUEST_CHANGES | None | None |  |  |
| `20260801-1413-pytorch-pytorch-PR191840-modal-gol` | pytorch/pytorch | 191840 | COMMENT | 0 | None |  |  |
| `20260801-1418-pytorch-pytorch-PR191831-modal-buy` | pytorch/pytorch | 191831 | COMMENT | 0 | None |  |  |
| `20260801-1424-pytorch-pytorch-PR191840-modal-pub` | pytorch/pytorch | 191840 | COMMENT | 0 | None |  |  |
| `20260801-1431-pytorch-pytorch-PR191831-modal-ins` | pytorch/pytorch | 191831 | COMMENT | 0 | None |  |  |
| `20260801-1436-pytorch-pytorch-PR191840-modal-ops` | pytorch/pytorch | 191840 | COMMENT | 0 | None |  |  |
| `20260801-1442-pytorch-pytorch-PR191831-modal-ent` | pytorch/pytorch | 191831 | COMMENT | 0 | None |  |  |
| `20260801-1445-pytorch-pytorch-PR191840-modal-com` | pytorch/pytorch | 191840 | COMMENT | 0 | None |  |  |
| `20260801-1451-pytorch-pytorch-PR191836-modal-gat` | pytorch/pytorch | 191836 | REQUEST_CHANGES | 12 | 1.0 | yes |  |
| `20260801-1502-pytorch-pytorch-PR191840-modal-gat` | pytorch/pytorch | 191840 | REQUEST_CHANGES | 7 | 1.0 | yes |  |
| `20260801-1511-pytorch-pytorch-PR191840-modal-qui` | pytorch/pytorch | 191840 | APPROVE | 7 | 1.0 | yes |  |

## Refresh

```bash
python3 scripts/quieter_over_time.py report
python3 scripts/torii.py quieter -- status
```
