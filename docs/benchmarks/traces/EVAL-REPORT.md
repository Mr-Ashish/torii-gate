# Torii eval-trace report (F83)

Generated: `2026-08-01T01:48:57Z`

## Aggregate

- runs: **14** (modal=6, local=8)
- log_streaming true: **4**
- fitness composite n=8
- composite mean/median/min/max: **0.842** / 0.8494 / 0.77 / 0.8694
- levels: `{"L2": 4, "L3": 4, "modal-f80-live": 1, "modal-f81-llm-critic": 1, "modal-f82-skills": 1, "modal-f83-pack-eval": 1, "\u2014": 2}`
- models: `deepseek/deepseek-v4-pro`, `fixture`

## Runs

| Archived | Host | Repo | PR | Model | Composite | Level | Feature | Dir |
|----------|------|------|----|-------|-----------|-------|---------|-----|
| 2026-08-01T00:14:28Z | local | torii/demo | 0 | `fixture` | 0.7700 | L2 | F73 | `20260801-0014-torii-demo-PR0-fixture-insecure-good-6ac1627` |
| 2026-08-01T00:16:02Z | local | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | 0.8694 | L3 | F73 | `20260801-0016-pytorch-pytorch-PR191813-pytorch-pr191813-172d21b` |
| 2026-08-01T00:23:52Z | local | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | 0.8694 | L3 | F73 | `20260801-0023-pytorch-pytorch-PR191813-pytorch-pr191813-f74-7e1a3b8` |
| 2026-08-01T00:31:45Z | local | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | 0.8694 | L3 | F73 | `20260801-0031-pytorch-pytorch-PR191813-pytorch-pr191813-f75-8809641` |
| 2026-08-01T00:38:51Z | local | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | 0.8294 | L2 | F73 | `20260801-0038-pytorch-pytorch-PR191813-pytorch-pr191813-f76-a52db5b` |
| 2026-08-01T00:45:14Z | local | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | 0.8294 | L2 | F73 | `20260801-0045-pytorch-pytorch-PR191813-pytorch-pr191813-f77-28220cc` |
| 2026-08-01T00:53:19Z | local | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | 0.8694 | L3 | F73 | `20260801-0053-pytorch-pytorch-PR191813-pytorch-pr191813-f78-fd45d45` |
| 2026-08-01T01:00:38Z | local | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | 0.8294 | L2 | F73 | `20260801-0100-pytorch-pytorch-PR191813-pytorch-pr191813-f79-1b7daed` |
| 2026-08-01T01:07:59Z | modal | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | — | modal-f80-live | F80 | `20260801-0107-pytorch-pytorch-PR191813-modal-f80` |
| 2026-08-01T01:25:06Z | modal | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | — | modal-f81-llm-critic | F81 | `20260801-0125-pytorch-pytorch-PR191813-modal-f81` |
| 2026-08-01T01:31:08Z | modal | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | — | modal-f82-skills | F82 | `20260801-0131-pytorch-pytorch-PR191813-modal-f82` |
| 2026-08-01T01:37:52Z | modal | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | — | modal-f83-pack-eval | F83 | `20260801-0137-pytorch-pytorch-PR191813-modal-f83` |
| — | modal | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | — | — | F84 | `20260801-0140-pytorch-pytorch-PR191813-modal-f84` |
| — | modal | pytorch/pytorch | 191813 | `deepseek/deepseek-v4-pro` | — | — | F85 | `20260801-0148-pytorch-pytorch-PR191813-modal-f85` |

## Notes

- Vault entries are redacted for paper/eval use; large agent.log may be gitignored.
- Modal rows may omit composite when fitness was scored only in-container.
- Source of truth paths: `docs/benchmarks/traces/*/summary.json`.

