# F113 research note — Dual-gate adopt of memory-CLI recovery skill

**Date:** 2026-08-01  
**Fire:** F113

## Sources

1. SkillsBench / F86 dual-rollout: contribution_pp > 0.
2. F88 LOO attribution: free-riders do not adopt.
3. F112 proposal from F106 recovery; skill_auto_adopt was f74-only.

## Pattern

| Gate | Role |
|------|------|
| validate_proposal | structure/safety/evidence |
| F86 dual | pack contribution_pp > 0 |
| F88 attr | solo/unique keywords |
| F113 globs | skill-prefer-* + skill-f74-* |

## Success

- candidates includes skill-prefer-memory-cli-early when not active
- adopt → agent/skills/active/
- dual_pass true; free_rider false
