# F78 research note — multi-checker second-agent critic

**Date:** 2026-08-01  
**Fire:** F78

## Sources

1. **QASecClaw** (arXiv 2605.01885): multi-agent SAST + validation agents for FP cut.
2. **VulAgent / Argus**: discovery vs confirmation split.
3. **Loop Engineering loop-verifier**: independent checker, default REJECT until evidence.
4. Prior Torii F70–F75 checkers existed but were not orchestrated as one post-run panel.

## Pattern

| Role | Implementation |
|------|----------------|
| Maker | Hermes agent review |
| Checker panel | F70 dual critic + F72 chain + F73 fitness + F75 memory + structure |
| Demote | Weak APPROVE without path evidence → COMMENT/REQUEST_CHANGES |
| Cost | Zero extra LLM (tools-as-code) |

## Success metric

- Offline: good composite ≫ weak; weak APPROVE demoted; inject marker
- Live: `second-agent-critic.json` in out_dir; SECOND_CRITIC=1 in meta
