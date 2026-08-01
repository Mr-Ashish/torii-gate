# F123 research note — Recovery skill loop packaging (traces + brand)

**Date:** 2026-08-01  
**Fire:** F123

## Sources

1. Agent skills packaging 2026: skills without lifecycle packaging do not compound in product UX.
2. Torii F119–F122 shipped measured recovery (always budget → compact → util → re-prompt).
3. Loop-eng scorecard + paper traces: ops need one readiness surface.

## Gap

Recovery loop was real in scripts but not closed in **trace archive**, **skill-loop scorecard**, or **landing** — installers and paper could miss inject_chars / util_rate artifacts.

## Pattern

| Surface | Role |
|---------|------|
| save-trace | Archive skill-router, skill-hits, recovery-util, re-prompt env, critic JSON |
| skill_loop_status | Stages + recovery_active + hermes F122 + save-trace wire |
| PRODUCT / landing / TORII.md | Mental model D: inject is not enough |
| EVAL-REPORT | F120–F122 metrics (prior fire) |

## Success

- skill_loop_status fixture recovery_ok + L3
- save-trace copies recovery-skill-util.json
- Brand landing shows recovery pipeline
