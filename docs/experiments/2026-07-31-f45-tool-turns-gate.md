# Fire — F45 tool-turns gate / H12 (2026-07-31)

## Problem

Odoo e2e PR #2 cheap path (`openai/gpt-4.1-mini`, hermes chat fallback):
`tool_turns=0` still **APPROVE**’d a multi-file code PR. GHA tool-using run on
the same PR correctly **REQUEST CHANGES** (missing format:false alias tests).
Agentic review without tools is not trustworthy enough to green-light merge.

## Evidence

- F44 run: `.torii-out-e2e-pr2-f44/` · `tool_turns=0` · score 25/50
- Offline F45 re-apply on F44 body → APPROVE→COMMENT, score cap 55, F45 banner

## Ship

- `scripts/tool_turns_gate.py` decide/apply (default on; docs-only / single-file exempt)
- `run-hermes-review.sh` post-normalize gate → `tool-turns-gate.env` + job summary
- `pack-run-for-ui.py` signal `tool_turns_gate` + chip `tool-turns-gate`
- `save-trace.sh` copies gate + sibling ops env files into traces
- `install-torii.sh` runtime allowlist
- tests: `test_tool_turns_gate.py` + pack signal

## Verify

```bash
pytest tests/test_tool_turns_gate.py tests/test_pack_run_for_ui.py -q
bash -n scripts/run-hermes-review.sh
python3 scripts/tool_turns_gate.py apply \
  --review .torii-out-e2e-pr2-f44/review-2.md \
  --out /tmp/r.md --tool-turns 0 --file-count 4 \
  --path a.js --path b.js --path c.js --path d.js
python3 scripts/parse-verdict.py /tmp/r.md  # verdict=COMMENT
```

## Knobs

| Var | Default | Meaning |
|-----|---------|---------|
| `TORII_TOOL_TURNS_GATE` | `1` | `0`/`off` disables |
| `TORII_TOOL_TURNS_MIN_FILES` | `2` | multi-file threshold |
| `TORII_TOOL_TURNS_GATE_VERDICTS` | `APPROVE` | which verdicts get rewritten |
