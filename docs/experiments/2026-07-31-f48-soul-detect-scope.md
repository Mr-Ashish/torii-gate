# F48 — Scope SOUL detect + agent.log capture to this invocation (H17)

## Trigger

H16 live mini on Mr-Ashish/odoo#2 (`openai/gpt-4.1-mini`, post-F47):

- `hermes -z` succeeded (no argv rejection, no chat fallback).
- `tool_turns=0` (model single-shot) → F45 COMMENT/55.
- Ops reported `soul_blocked=1` while **this-run** `hermes-run.log` had no SOUL block line.

## Root cause

`capture-hermes-loop.py` copied the last 200k of shared `$HERMES_HOME/logs/agent.log`,
which still contained an older session warning:

`Context file SOUL.md blocked: prompt_injection`

F46 detect scanned that package → false positive.

## Fix

1. Export `HERMES_LOG_OFFSET` (byte offset snapshotted before hermes) into capture.
2. Capture writes only `agent.log[offset:]` when offset is valid.
3. Document that detect must not treat full shared log history as this-run signal.

## Verify

- `python3 -m unittest tests.test_soul_context_scan -v`
- Reconstructed H16 slice: no `SOUL.md blocked`; full log: has it.
