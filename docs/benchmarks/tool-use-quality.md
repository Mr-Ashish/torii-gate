<!-- torii-tool-use-quality -->

# Agent tool-use quality

_Generated: `2026-08-02T03:02:55Z` · feature **TOOL_USE** · tool_use_ok=`True`_

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
| measured runs | 93 |
| tool_use_rate | 0.9032 |
| mean / median turns | 6.68 / 6 |
| zero-tool rate | 0.0968 (n=9) |
| solid+ rate (≥3 turns) | 0.8495 |
| deep rate (≥5 turns) | 0.6667 |
| quality_score | 0.8398 |
| quality_ok | True |

### Quality bands

| Band | count |
|------|------:|
| deep | 62 |
| solid | 17 |
| minimal | 5 |
| zero | 9 |

### Top tools (from agent-loop when present)

| Tool | n |
|------|--:|
| `terminal` | 551 |
| `read_file` | 55 |

## Recent dogfood rows

| trace | repo | pr | turns | band | loop |
|-------|------|---:|------:|------|:----:|
| `20260801-2238-pytorch-pytorch-PR191844-modal-gtm` | pytorch/pytorch | 191844 | 19 | deep |  |
| `20260801-2254-pytorch-pytorch-PR191840-modal-cus` | pytorch/pytorch | 191840 | 3 | solid |  |
| `20260801-2313-pytorch-pytorch-PR191840-modal-fs-` | pytorch/pytorch | 191840 | 9 | deep |  |
| `20260802-0019-pytorch-pytorch-PR191840-modal-tts` | pytorch/pytorch | 191840 | 8 | deep |  |
| `20260802-0042-pytorch-pytorch-PR191852-modal-qui` | pytorch/pytorch | 191852 | 7 | deep |  |
| `20260802-0105-pytorch-pytorch-PR191854-modal-lan` | pytorch/pytorch | 191854 | 11 | deep |  |
| `20260802-0121-pytorch-pytorch-PR191851-modal-pil` | pytorch/pytorch | 191851 | 23 | deep |  |
| `20260802-0139-pytorch-pytorch-PR191853-modal-mod` | pytorch/pytorch | 191853 | 5 | deep |  |
| `20260802-0154-pytorch-pytorch-PR191852-modal-sel` | pytorch/pytorch | 191852 | 8 | deep |  |
| `20260802-0211-pytorch-pytorch-PR191854-modal-org` | pytorch/pytorch | 191854 | 5 | deep |  |
| `20260802-0227-pytorch-pytorch-PR191851-modal-mem` | pytorch/pytorch | 191851 | 10 | deep |  |
| `20260802-0249-pytorch-pytorch-PR191852-modal-cer` | pytorch/pytorch | 191852 | 11 | deep |  |

## Refresh

```bash
python3 scripts/tool_use_quality.py report
python3 scripts/torii.py tool-use -- status
```
