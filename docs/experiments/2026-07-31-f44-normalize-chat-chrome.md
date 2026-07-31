# Fire — F44 normalize hermes chat chrome (2026-07-31)

## Problem

Odoo e2e PR #2 local run (`openai/gpt-4.1-mini`): `hermes -z` failed (rc=2),
fallback `hermes chat -q` echoed `Query:` + full prompt (including the Markdown
**template** with every REQUIRED_SNIPPET). `normalize-review.py` treated the
blob as contract-OK → would post the prompt to GitHub. Verdict parse failed
(`verdict=None` in run-bundle). Horizontal `───` finding separators were later
mistaken for TUI chrome when scrubbing.

## Evidence

- Run: `.torii-out-e2e-pr2-f44/` · trace `pr2-runlocal-a1`
- `tool_turns=0`, SOUL.md blocked `prompt_injection`
- GHA run on same PR correctly REQUEST CHANGES (missing format:false tests)

## Ship

- `scripts/normalize-review.py`: `extract_agent_review`, placeholder rejection,
  loose-heading promotion, safer chrome filter (no bare ─── as chrome)
- `tests/test_normalize_review.py`: F44 cases
- Benchmark + learn + ROI docs for multi-PR corpus

## Verify

```bash
pytest tests/test_normalize_review.py -q
python3 scripts/normalize-review.py -i .torii-out-e2e-pr2-f44/review-2.raw.md \
  -o /tmp/r.md --pr 2 && python3 scripts/parse-verdict.py /tmp/r.md
```
