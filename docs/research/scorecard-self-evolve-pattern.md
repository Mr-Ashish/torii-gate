# F132 research note — Self-evolve skills from scorecard gaps

**Date:** 2026-08-01  
**Fire:** F132

## Sources

1. **Survey of Self-Evolving Agents** (arXiv 2507.21046): inter-test-time evolution from feedback without weight updates.
2. **Agent Skill Evaluation & Evolution** (arXiv 2606.11435): measure → propose → eval → adopt.
3. EvoSkills / Skill-MAS: evaluation gaps drive skill library growth.
4. F129–F131 product scorecard without evolution leaves readiness gaps static.

## Pattern

| Input | Output |
|-------|--------|
| product-scorecard.json metrics | gap keys (bool/level only) |
| SCORECARD_GAP_TEMPLATES | skill proposal markdown |
| agent/skills/proposals/ | privacy-safe skill drafts |
| install guide | dual compound + propose-scorecard |

## Env

- `TORII_SELF_EVOLVE_SCORECARD=1` (default) post-run soft propose
- `--scorecard PATH` / dry-run

## Success

- Gaps → ≥1 proposal; no `/Users/` in skill body
- Install guide contains Dual compound + propose-scorecard
