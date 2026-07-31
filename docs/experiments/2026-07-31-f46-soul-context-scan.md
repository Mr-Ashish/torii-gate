# Fire — F46 SOUL context scan / H13 (2026-07-31)

## Problem

Hermes loads `$HERMES_HOME/SOUL.md` through `_scan_context_content` (scope=context).
Torii’s trust-model section **quoted** the classic attack phrase
`ignore previous instructions`, which matches Hermes `threat_patterns`
`prompt_injection`. Result (odoo e2e F44):

```
Context file SOUL.md blocked: prompt_injection
```

The entire reviewer contract was replaced with a `[BLOCKED: …]` stub — silent
quality loss (D8 memory/context).

## Ship

- `agent/SOUL.md`: rephrase trust model without classic injection quotes
- `scripts/soul_context_scan.py` check/detect (mirror blocking patterns)
- `run-hermes-review.sh` preflight after SOUL copy + post-run log detect →
  `soul-context.env` / job summary
- pack chip `soul-blocked`; install pack + save-trace
- tests: product SOUL must stay clean; dirty phrase still detected

## Verify

```bash
python3 scripts/soul_context_scan.py check          # clean=1
# against Hermes itself (when pin present):
python3 -c 'import sys; sys.path.insert(0,".torii-hermes-home/hermes-agent");
from tools.threat_patterns import scan_for_threats; print(scan_for_threats(open("agent/SOUL.md").read(), scope="context"))'
pytest tests/test_soul_context_scan.py -q
```
