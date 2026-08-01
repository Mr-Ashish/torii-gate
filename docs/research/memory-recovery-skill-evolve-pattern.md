# F112 research note — Self-evolve skill from F106 memory recovery

**Date:** 2026-08-01  
**Fire:** F112

## Sources

1. Hermes self-evolution: trajectories → skill proposals → eval → adopt.
2. Torii F105/F106: measured utilization gap + soft re-prompt recovery (hits 0→5).
3. Mem2ActBench: proactive memory use beats passive inject.

## Pattern

| Signal | Source artifact | Proposal |
|--------|-----------------|----------|
| `f106_recovered` | memory-tool-reprompt.env | skill-prefer-memory-cli-early |
| `memory_utilization_gap` | memory-tool-audit.json | same |
| `memory_tools_used` | audit tools_used | reinforcing |

## Success

- ingest emits f106_recovered / memory_tools_used
- propose creates skill-prefer-memory-cli-early when recovery signals present
- dual-gate adopt still required (no silent auto-adopt)
