# F115 research note — Tool-outcome LOO attribution + dual contribution

**Date:** 2026-08-01  
**Fire:** F115

## Sources

1. **Mem2Act / proactive memory:** inject ≠ utilization; measure tool calls.
2. **SkillsBench / F86:** contribution_pp = with − ablated hit rates (prose-only was incomplete).
3. **Assay / “Not All Skills Help”:** LOO masking retires free-riders — must not mis-label tool-only skills.
4. **Hermes self-evolution:** multi-dim fitness + constraints before adopt.
5. **Torii F114:** tool_hit scored in `skill_router.score_hits`; F113 adopted `skill-prefer-memory-cli-early`.

## Gap

F114 measures tool invocations, but F88 LOO attribution and F86 dual-rollout only used **review prose**. Recovery skills that succeed via `torii.py memory` would look like free-riders (or zero dual contribution) when the review body is silent.

## Pattern

| Layer | Role |
|-------|------|
| F114 score | prose_hit OR tool_hit → combined hit |
| F115 LOO | tool_hit → +1.5 contribution; tool_unique; free_rider only if neither |
| F115 dual | tool_blob_with (taught CLIs) vs tool_blob_ablated (generic shell) |
| F89 ledger | `tool_hits` compound; tool-effective skills skip free-rider demote |
| Router | ranking prefers tool-proven recovery skills |

## Env

- `TORII_SKILL_ATTR_TOOL=1` (default) — LOO tool credit
- `TORII_SKILL_DUAL_TOOL=1` (default) — dual tool contribution

## Success metric

- Offline: attribution fixture tool_attr_ok + tool_contrib_ok; dual tool_contribution_pp ≥ 0 and with tool_hit_n ≥ 1
- Live: cycle from review with agent-loop credits tool contributors; Modal BIT3_OK
