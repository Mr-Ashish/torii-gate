# F68 + F69 — Agent tools pipeline + Torii-native self-evolution

**Date:** 2026-08-01  
**Status:** shipping  
**Tag:** PRODUCT_FEATURE | AGENT_QUALITY | MEMORY | HERMES_PATTERNS

## F68 — Agent tools (research → eval → adopt)

### Problem

Tool/toolset choices were implicit (`TORII_TOOLSETS=terminal`) with no durable
loop from run evidence → candidates → scored adopt. Hermes ROI backlog (H3–H10…)
sat as docs only.

### Fix

`scripts/agent_tools_pipeline.py`:

| Stage | Action |
|-------|--------|
| **research** | Scan `agent-loop.json` trees + `hermes-inspired-roi.md` backlog → `catalog.candidates` |
| **eval** | Offline heuristic dims (signal/safety/effort/fit/cost) → `recommend=adopt\|hold\|design` |
| **adopt** | Promote → `agent/tools/catalog.json` + `agent/tools/adopted/{id}.json` + `active-toolsets.txt` |
| **toolsets** | Print comma-separated toolsets for `TORII_TOOLSETS` |

Orchestrator loads active toolsets when `TORII_TOOLSETS` unset. Auto-adopt remains
opt-in (`TORII_AGENT_TOOLS_AUTO_ADOPT=0` default). Research stage opt-in via
`TORII_AGENT_TOOLS_RESEARCH=1`.

## F69 — Hermes best practices as Torii-native self-evolution

### Problem

Hermes self-evolution (skill files, GEPA/DSPy, trajectory datasets) is valuable
but must **not** be a Hermes fork. Torii needed a control-plane native loop.

### Patterns adopted (from ROI H3/H9/H10)

| Hermes idea | Torii-native |
|-------------|--------------|
| Trajectory packaging (H9) | `self_evolve.py ingest` → `memory/evolution/trajectories/` |
| Skill-file evolution (H3) | propose → eval → adopt markdown skills under `agent/skills/` |
| Soft skill nudge (H10) | inject soft nudge from recent zero-tool/F49 trajectories |

### Fix

`scripts/self_evolve.py`:

| Stage | Action |
|-------|--------|
| **ingest** | Package OUT_DIR agent-loop + signals |
| **propose** | Skill proposals from signal aggregates |
| **eval** | Structure/actionability/evidence score |
| **adopt** | → `agent/skills/active/` |
| **inject** | Assemble-time prompt injection (`<!-- torii-f69-skills -->`) |

Orchestrator always soft-ingests after save_trace. Auto propose/eval when
`TORII_SELF_EVOLVE=1`. Adopt stays human-gated.

## Tests

```bash
pytest tests/test_agent_tools_pipeline.py tests/test_self_evolve.py -q
```

## Verify

```bash
python3 scripts/agent_tools_pipeline.py status
python3 scripts/self_evolve.py status
python3 scripts/self_evolve.py inject --prompt /tmp/p.md
```
