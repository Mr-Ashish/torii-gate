<!-- torii-tool-use-quality -->

# Agent tool-use quality

_Generated: `2026-08-01T16:39:05Z` · feature **TOOL_USE** · tool_use_ok=`True`_

**One-liner:** Agent tool-use quality: tools-as-code chart, not SOUL prose

Buyer story: the merge-authority agent **reads the change with tools** — not a chat-only skim. Fail-closed `tool_turns_gate` blocks empty APPROVE.

Buyer doc: [`docs/TOOL-USE.md`](../TOOL-USE.md) · Quieter: [`quieter-over-time.md`](quieter-over-time.md)

## Readiness (tools-as-code)

| Metric | Value |
|--------|------:|
| checks ok | 8/8 |
| catalog adopted | 37/37 |

| Check | Pass |
|-------|:----:|
| `tool_turns_gate_script` | yes |
| `trajectory_fitness_script` | yes |
| `agent_tools_pipeline` | yes |
| `tool_use_quality_script` | yes |
| `buyer_doc` | yes |
| `catalog` | yes |
| `gate_doc_mentions_tools` | yes |
| `tool_turns_default_on` | yes |

## Dogfood aggregate

| Metric | Value |
|--------|------:|
| measured runs | 61 |
| tool_use_rate | 0.8525 |
| mean / median turns | 5.56 / 6 |
| zero-tool rate | 0.1475 (n=9) |
| solid+ rate (≥3 turns) | 0.7705 |
| deep rate (≥5 turns) | 0.5902 |
| quality_score | 0.7754 |
| quality_ok | True |

### Quality bands

| Band | count |
|------|------:|
| deep | 36 |
| solid | 11 |
| minimal | 5 |
| zero | 9 |

### Top tools (from agent-loop when present)

| Tool | n |
|------|--:|
| `terminal` | 350 |
| `read_file` | 36 |

## Recent dogfood rows

| trace | repo | pr | turns | band | loop |
|-------|------|---:|------:|------|:----:|
| `20260801-1527-pytorch-pytorch-PR191840-modal-com` | pytorch/pytorch | 191840 | 3 | solid | yes |
| `20260801-1535-pytorch-pytorch-PR191840-modal-wor` | pytorch/pytorch | 191840 | 2 | minimal | yes |
| `20260801-1541-pytorch-pytorch-PR191840-modal-fed` | pytorch/pytorch | 191840 | 6 | deep | yes |
| `20260801-1546-pytorch-pytorch-PR191840-modal-sel` | pytorch/pytorch | 191840 | 6 | deep | yes |
| `20260801-1552-pytorch-pytorch-PR191840-modal-mem` | pytorch/pytorch | 191840 | 7 | deep | yes |
| `20260801-1558-pytorch-pytorch-PR191840-modal-gtm` | pytorch/pytorch | 191840 | 9 | deep | yes |
| `20260801-1605-pytorch-pytorch-PR191840-modal-ops` | pytorch/pytorch | 191840 | 8 | deep | yes |
| `20260801-1610-pytorch-pytorch-PR191840-modal-bra` | pytorch/pytorch | 191840 | 4 | solid | yes |
| `20260801-1618-pytorch-pytorch-PR191840-modal-cos` | pytorch/pytorch | 191840 | 3 | solid | yes |
| `20260801-1624-pytorch-pytorch-PR191840-modal-lan` | pytorch/pytorch | 191840 | 6 | deep | yes |
| `20260801-1630-pytorch-pytorch-PR191840-modal-pro` | pytorch/pytorch | 191840 | 5 | deep | yes |
| `20260801-1636-pytorch-pytorch-PR191840-modal-rea` | pytorch/pytorch | 191840 | 6 | deep | yes |

## Refresh

```bash
python3 scripts/tool_use_quality.py report
python3 scripts/torii.py tool-use -- status
```
