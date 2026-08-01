## Skill compound loop readiness (F91)

**Loop:** `route → hit → fitness → dual → attr → inject → util → budgeted re-prompt`  ·  **Level:** L3  ·  **100.0%**

Skills that do not contribute do not ship in the next prompt.

| Stage | Feature | Script | Pack | OK |
|-------|---------|--------|:----:|:--:|
| route | F84 | `skill_router.py` | ✓ | ✓ |
| hit | F84/F114 | `skill_router.py` | ✓ | ✓ |
| fitness | F85/F116 | `skill_fitness.py` | ✓ | ✓ |
| dual | F86/F115 | `skill_dual_rollout.py` | ✓ | ✓ |
| attr | F88/F115 | `skill_attribution.py` | ✓ | ✓ |
| inject | F89/F119/F120 | `skill_router.py` | ✓ | ✓ |
| adopt_gate | F87/F118 | `skill_auto_adopt.py` | ✓ | ✓ |
| recovery_util | F121 | `skill_router.py` | ✓ | ✓ |
| recovery_reprompt | F122 | `reprompt_budget.py` | ✓ | ✓ |

- Active skills: **9** (skill-archival-memory-search, skill-f74-exploit-scenario, skill-f74-prefer-chain-json, skill-prefer-critic-early, skill-prefer-memory-cli-early, skill-prefer-product-cli)
- Recovery skills (memory/product/critic): **ok** (skill-prefer-memory-cli-early, skill-prefer-product-cli, skill-prefer-critic-early)
- Wiring (assemble/run/hermes/save-trace): **ok**
- Deep fixtures: **skipped/fail**
- Ready: **True**
