# Torii Gate — agent tool-use quality

**Buyer story:** the merge-authority agent **uses tools on the diff** — not chat-only skim.

```text
PR → Hermes + tools (terminal/diff/CLI) → path-evidenced review → torii/gate
         ↑
   tool_turns_gate fail-closed if zero tools on multi-file code PRs
```

## Why this matters

Empty APPROVE without workspace/diff reads is worse than a closed gate. Torii:

1. **Measures** tool turns on every dogfood run (`tool_call_turns` / agent-loop).
2. **Gates** zero-tool multi-file approvals (`tool_turns_gate` — default on).
3. **Publishes** a vault chart operators can open without reading Hermes prose.

## Product surface

```bash
python3 scripts/tool_use_quality.py report
python3 scripts/torii.py tool-use -- status
# → docs/benchmarks/tool-use-quality.md
```

| Signal | Good looks like |
|--------|-----------------|
| **tool_use_rate** | majority of measured runs ≥1 tool turn |
| **mean turns** | deep enough to read changed files (often 3–7 on real PRs) |
| **zero-tool rate** | low; remaining zeros are docs/trivial or fail-closed |
| **quality_score** | composite of use + solid (≥3) + deep (≥5) rates |

Related:

- Fail-closed inventory: [`docs/ops/RELIABILITY.md`](ops/RELIABILITY.md)
- Trajectory fitness (tool_use dim 0.20): `scripts/trajectory_fitness.py`
- Quieter-over-time (includes tool use): [`QUIETER.md`](QUIETER.md)
- Adopted agent tools catalog: `agent/tools/catalog.json`

## Operator habit

1. Keep `TORII_TOOL_TURNS_GATE` unset (default **on**).
2. Dogfood with Modal/local; confirm Hermes logs show tool turns in Modal UI.
3. Refresh the chart after a batch of runs:

```bash
python3 scripts/torii.py tool-use -- report
python3 scripts/torii.py quieter -- status
```

## What this is *not*

- Not a new compound-loop feature stack (no F185+).
- Not “more SOUL prose about tools.”
- Not auto-merge.

It is: **tools-as-code measurement + fail-closed defaults** for merge authority.
