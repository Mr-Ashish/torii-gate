<!-- F118/F119/F120 compact recovery skill -->
---
id: skill-prefer-product-cli
feature: F117/F118/F120
status: adopted
always: true
always_priority: 90
signal: f117_product_cli_tools
title: Call torii product CLI doctor/status early
---

## Skill: prefer-product-cli

1. Early mid-review call once:
   `python3 scripts/torii.py doctor` or `python3 scripts/torii.py status`
   `python3 scripts/torii.py budget -- status` when soft re-prompts are possible.
2. Treat doctor/status as readiness hints only — still require path:line evidence.
3. Prefer product CLI over ad-hoc script hunting for memory/gate/budget surfaces.
