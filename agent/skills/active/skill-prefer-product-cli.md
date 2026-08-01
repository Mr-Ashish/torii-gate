<!-- F118 dual-gate tool-attr adopted -->
<!-- F74 adopted 2026-08-01T05:36:49Z -->
---
id: skill-prefer-product-cli
feature: F117/F118
status: adopted
signal: f117_product_cli_tools
created_at: 2026-08-01T05:35:12Z
title: Call torii product CLI doctor/status early
---

## Skill: prefer-product-cli (F117)

When the product umbrella CLI is available (F110):
1. Early mid-review call once:
   `python3 scripts/torii.py doctor` or `python3 scripts/torii.py status`
   `python3 scripts/torii.py budget -- status` when soft re-prompts are possible.
2. Use doctor/status as readiness hints only — still require path:line evidence.
3. Prefer product CLI over ad-hoc script hunting for memory/gate/budget surfaces.

