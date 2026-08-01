# Torii Gate — workflows as code

**Buyer story:** the merge-authority pipeline is a **declarative graph** (stages, soft/hard fail, scripts on disk) — not an LLM prose recipe.

```text
preload → assemble → Hermes (tools) → save-trace + certificate
                  → checker panel → memory/skill compound → torii/gate
```

## Why this matters

Chatbots invent steps. Torii ships a **workflow YAML** operators can read, validate, and version with the pack:

| Property | Meaning |
|----------|---------|
| **Deterministic stages** | Named scripts, soft vs hard fail — no ad-hoc agent plan |
| **Validate offline** | `workflow -- validate` before you burn OpenRouter $ |
| **Install matrix** | Which capabilities ship in the pack (install guide) |
| **Scorecard L3** | Triple-ready with skill + memory loops (`workflow -- scorecard`) |

Source of truth: [`docs/workflows/torii-gate.workflow.yaml`](workflows/torii-gate.workflow.yaml).

## Operator commands

```bash
python3 scripts/torii.py workflow -- validate
python3 scripts/torii.py workflow -- status
python3 scripts/torii.py workflow -- scorecard
python3 scripts/torii.py workflow -- fixture
# install guide (capability matrix):
python3 scripts/workflow_as_code.py install-guide
```

Offline smoke still covers the gate path:

```bash
./scripts/smoke-torii-gate.sh
```

## How it fits the commercial path

1. **Install** pack → workflow files land in the app repo.  
2. **Require** status check **`torii/gate`**.  
3. **Review** runs the workflow stages (Hermes tools + checker + certificate).  
4. **Measure** quieter / tool-use / cost on dogfood.

Related: [`GOLDEN-PATH.md`](GOLDEN-PATH.md) · [`GATE.md`](GATE.md) · [`QUIETER.md`](QUIETER.md) · [`TOOL-USE.md`](TOOL-USE.md) · install: [`INSTALL.md`](INSTALL.md).

## What this is *not*

- Not a new compound-loop F-stack for every PR.
- Not “SOUL tells the agent the pipeline.”
- Not auto-merge.

It is: **workflows-as-code** so merge authority stays auditable and installable.
