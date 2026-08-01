# F140 research note — Scorecard hub attribution LOO floor

**Date:** 2026-08-01  
**Fire:** F140

## Sources

1. F127 hub_ingested recovery floor in skill_attribution LOO.
2. Assay / "Not All Skills Help": free-rider retirement without multi-tenant shield.
3. F138/F139 scorecard hub post-score + critic without attr floor demotes ops skills.
4. FederatedSkill: themes not trajectories — attribution must honor hub evidence.

## Pattern

| Layer | Role |
|-------|------|
| fitness scorecard_ops / scorecard_ingested_n | F135 local ops evidence |
| post_score_scorecard_hub deltas | F138 multi-tenant priority |
| attribute() scorecard floor | ≥0.85 (tool_hit → ≥1.0) |
| free_rider | blocked when scorecard_floor |

## Env

- `TORII_SKILL_ATTR_SCORECARD=1` (default)

## Success

- Fixture f140_ok: silent review + scorecard skill floored, not free-rider
- Off-flag becomes free-rider; privacy skill ids only
