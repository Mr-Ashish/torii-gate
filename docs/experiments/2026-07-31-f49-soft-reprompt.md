# Fire — F49 soft tool-turns re-prompt / H15 (2026-07-31)

## Problem

After F47 (`hermes -z` reliable) + F48 (SOUL detect scoped), cheap multi-file
runs on odoo e2e **#2** and **#4** still end with `tool_turns=0` (model
single-shot). F45 fail-closes honesty (COMMENT/55) but does not recover signal
quality (D1). Need one recovery attempt before fail-closed.

## Ship

- `scripts/tool_turns_gate.py`:
  - `should_reprompt` / `build_reprompt_suffix` / `write_reprompt_prompt`
  - CLI `reprompt-decide` + `reprompt-write`
  - knob `TORII_TOOL_TURNS_REPROMPT` (default on)
- `run-hermes-review.sh`: after first capture, if eligible → archive attempt-1 →
  second `hermes -z` with nudged prompt → re-capture → `tool-turns-reprompt.env`
- `pack-run-for-ui.py` signals + chips `tool-reprompt` / `tool-reprompt-ok`
- `save-trace.sh` copies reprompt env + attempt-1 loop
- tests: `test_tool_turns_gate.py` (RepromptTests) + pack signal tests

## Flow

1. First `hermes -z` + capture
2. `reprompt-decide` (zero tools + multi-file code + not already)
3. Soft re-prompt once → re-capture
4. Normalize + **F45** (still fires if tools remain 0)

## Verify

```bash
pytest tests/test_tool_turns_gate.py tests/test_pack_run_for_ui.py -q
bash -n scripts/run-hermes-review.sh
python3 scripts/tool_turns_gate.py reprompt-decide --tool-turns 0 --file-count 4 --path a.js --path b.js
```

## Knobs

| Var | Default | Meaning |
|-----|---------|---------|
| `TORII_TOOL_TURNS_REPROMPT` | `1` | `0`/`off` disables second pass |
| `TORII_TOOL_TURNS_MIN_FILES` | `2` | shared with F45 |
