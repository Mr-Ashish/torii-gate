# F133 research note — Dual-gate adopt of scorecard-gap skills

**Date:** 2026-08-01  
**Fire:** F133

## Sources

1. SkillOpt / dual-gate adopt: default REJECT until dual contribution + attribution.
2. F132 propose-scorecard without adopt leaves proposals inert.
3. Loop-eng verifier before merge into active skills.
4. Mem2Act: tool_blob attribution for tool-taught ops skills.

## Pattern

| Step | Action |
|------|--------|
| propose | self_evolve.propose_from_scorecard |
| list | list_candidates(scorecard_only=True) |
| gate | F87 dual + F78 critic offline |
| attr | F118 tool blobs for F132 skill ids |
| adopt | fitness_gate recommend=adopt only |

## Env

- `TORII_SKILL_AUTO_ADOPT_SCORECARD=0` default in review; set `1` to soft-adopt
- CLI: `python3 scripts/skill_auto_adopt.py cycle-scorecard`

## Success

- Fixture f133_adopt_ok + active; tool attr > 0
- Malicious still blocked
