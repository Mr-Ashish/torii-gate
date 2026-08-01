# F89 research note — attribution-ranked skill inject

**Date:** 2026-08-01  
**Fire:** F89

## Sources

1. Assay / Not All Skills Help: per-task masking + retire inert skills.
2. Prior F88: LOO attribution at adopt time only — inject still path-ranked.
3. F85 fitness demote pattern: durable ledger → router score delta.

## Pattern

| Artifact | Role |
|----------|------|
| skill_attribution cycle | post-run LOO → `.torii/skill-attribution.json` |
| router_boosts | avg_contribution → positive score |
| free_rider_set | majority free-rider → skip full inject |
| skill_router select | attr_boost + free_rider_skipped |

Env: `TORII_SKILL_ATTR_ROUTER=1` (default), `TORII_SKILL_ATTR_ROUTER_BOOST` max delta.

## Success metric

- fixture: zombie free_rider in set; chain boost > 0
- select: free_rider_skipped contains free-rider; contributor selected
