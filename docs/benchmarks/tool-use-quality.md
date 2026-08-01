<!-- torii-tool-use-quality -->

# Agent tool-use quality

_Generated: `2026-08-01T15:23:09Z` · feature **TOOL_USE** · tool_use_ok=`True`_

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
| measured runs | 49 |
| tool_use_rate | 0.8163 |
| mean / median turns | 5.59 / 6 |
| zero-tool rate | 0.1837 (n=9) |
| solid+ rate (≥3 turns) | 0.7347 |
| deep rate (≥5 turns) | 0.5714 |
| quality_score | 0.7429 |
| quality_ok | True |

### Quality bands

| Band | count |
|------|------:|
| deep | 28 |
| solid | 8 |
| minimal | 4 |
| zero | 9 |

### Top tools (from agent-loop when present)

| Tool | n |
|------|--:|
| `terminal` | 144 |
| `read_file` | 6 |

## Recent dogfood rows

| trace | repo | pr | turns | band | loop |
|-------|------|---:|------:|------|:----:|
| `20260801-0505-pytorch-pytorch-PR191813-modal-f11` | pytorch/pytorch | 191813 | None | unknown |  |
| `20260801-1413-pytorch-pytorch-PR191840-modal-gol` | pytorch/pytorch | 191840 | 0 | zero |  |
| `20260801-1418-pytorch-pytorch-PR191831-modal-buy` | pytorch/pytorch | 191831 | 0 | zero |  |
| `20260801-1424-pytorch-pytorch-PR191840-modal-pub` | pytorch/pytorch | 191840 | 0 | zero |  |
| `20260801-1431-pytorch-pytorch-PR191831-modal-ins` | pytorch/pytorch | 191831 | 0 | zero |  |
| `20260801-1436-pytorch-pytorch-PR191840-modal-ops` | pytorch/pytorch | 191840 | 0 | zero |  |
| `20260801-1442-pytorch-pytorch-PR191831-modal-ent` | pytorch/pytorch | 191831 | 0 | zero |  |
| `20260801-1445-pytorch-pytorch-PR191840-modal-com` | pytorch/pytorch | 191840 | 0 | zero |  |
| `20260801-1451-pytorch-pytorch-PR191836-modal-gat` | pytorch/pytorch | 191836 | 12 | deep | yes |
| `20260801-1502-pytorch-pytorch-PR191840-modal-gat` | pytorch/pytorch | 191840 | 7 | deep | yes |
| `20260801-1511-pytorch-pytorch-PR191840-modal-qui` | pytorch/pytorch | 191840 | 7 | deep |  |
| `20260801-1519-pytorch-pytorch-PR191840-modal-too` | pytorch/pytorch | 191840 | 6 | deep | yes |

## Refresh

```bash
python3 scripts/tool_use_quality.py report
python3 scripts/torii.py tool-use -- status
```
