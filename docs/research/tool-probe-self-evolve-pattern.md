# F117 research note — Tool-probe self-evolution from live trajectories

**Date:** 2026-08-01  
**Fire:** F117

## Sources

1. Hermes self-evolution / GEPA-lite: trajectories → proposals → eval → adopt.
2. SigLeak / contrastive skill signatures: portable tool evidence, not raw code.
3. Trajectory eval 2026: tool path is first-class quality signal (F114–F116).
4. Gap: TOOL_OUTCOME_PROBES were static; live doctor/status/critic CLIs never entered F114 scoring.

## Pattern

| Layer | Role |
|-------|------|
| Catalog | Fixed allowlisted `pattern → skill` (no free-form log regex) |
| Mine | Observe catalog hits in agent-loop + skill-hits → durable ledger |
| Score | skill_router merges `.torii/tool-outcome-probes.json` into F114 probes |
| Propose | Novel families → skill-prefer-product-cli / skill-prefer-critic-early |
| Live | run-torii-review soft `mine-probes` after fitness; `--propose` if SELF_EVOLVE |

## Safety

- Only catalog patterns ever written to ledger
- Privacy: skill id + pattern + hit counts (no paths/snippets)
- Dual-gate adopt still via skill_auto_adopt (skill-prefer-*)

## Success

- Offline fixture: mine doctor+critic+memory; match_ok; proposals created
- Live Modal: mine stage soft; BIT3_OK
