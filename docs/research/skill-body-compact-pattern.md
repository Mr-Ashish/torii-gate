# F120 research note — SkillReducer-lite always body compact + pack verify

**Date:** 2026-08-01  
**Fire:** F120

## Sources

1. **SkillReducer** (arXiv 2603.29919): 39% body compression via progressive disclosure; separate core rules from background.
2. Agent Skills composition cliff: instruction bloat dilutes attention ~3k tokens.
3. Torii F119: always budget of 3 still injects ~3–4k chars of recovery prose.

## Pattern

| Layer | Role |
|-------|------|
| compact_skill_body | keep headings, numbered steps, code ticks; drop background |
| ALWAYS_MAX_CHARS | default 480 for always skills |
| FULL_MAX_CHARS | default 900 for scored full skills |
| install verify | pack dies if memory/product-cli/critic missing from active/ |

## Env

- `TORII_SKILL_COMPACT=1`
- `TORII_SKILL_ALWAYS_MAX_CHARS=480`
- `TORII_SKILL_FULL_MAX_CHARS=900`

## Success

- Offline fixture: f120_chars_saved ≥ 1; compact inject ≤ full inject
- install --dest includes three recovery skills
- Modal BIT3_OK
