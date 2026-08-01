# F165 — GEPA-lite skill refine-from-util

## Pattern
Read recovery/hub-archival util + fitness traces → diagnose inject≠tool → mutate active skill bodies with tool-first nudges → Hermes constraint gates (size ≤15KB, id, required probes).

## Offline
- `python3 scripts/self_evolve.py fixture-refine` → f165_ok

## Live local (Hermes DeepSeek V4 Pro)
- recall=1.0 tp=4 recovery_injected_n=3 util_rate=1.0
- skill-refine.json refined memory-cli-early (chronic_tool_miss) under constraints

## Modal
- pytorch/pytorch#191831 BIT3_OK ~89.6s log_streaming=true POST_COMMENT=0

## Product
- skill_loop `skill_refine_ok` / hermes soft wire after F163 fitness cycle
