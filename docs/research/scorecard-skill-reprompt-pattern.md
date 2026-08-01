# F137 research note — Scorecard util soft re-prompt

**Date:** 2026-08-01  
**Fire:** F137

## Sources

1. F122 recovery skill re-prompt: measure gap → one paid nudge under F108 budget.
2. SoK Agentic Skills: skill availability ≠ quality; idle skills need recovery loops.
3. Agent field notes 2026: recover after bad tool step with harness re-prompt.
4. F136 scorecard util gap without re-prompt left demote-only (no second chance).

## Pattern

| Layer | Role |
|-------|------|
| scorecard-skill-util.json | F136 mid-run util |
| decide_scorecard_reprompt | gap + tools≥1 → reprompt |
| composite reprompt-decide | OR recovery + scorecard (one attempt) |
| prompt marker | `<!-- torii-f137-scorecard-skill-reprompt -->` |
| CLIs | doctor / scorecard / demote-eval / workflow scorecard |
| budget | F108 kind f137 (scorecard-only) or f122 |

## Env

- `TORII_SCORECARD_SKILL_REPROMPT=1` (default)

## Success

- Fixture: gap→reprompt=1; good/none→0; zero tools defers F49; prompt has marker
- Privacy: no `/Users/`, no raw tenant
