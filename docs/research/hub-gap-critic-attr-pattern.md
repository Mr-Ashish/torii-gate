# F127 research note — Hub gap critic + hub_ingested attribution

**Date:** 2026-08-01  
**Fire:** F127

## Sources

1. QASecClaw / VulAgent: maker/checker — recovery util alone is local; hub gap is multi-tenant confirmation.
2. FederatedSkill + F126: gap_pressure already biases re-prompt; critic must also demote APPROVE.
3. Assay / LOO attribution: hub_ingested fitness skills need contribution floor or free-rider ledger kills recovery.
4. Loop-eng verifier panel: independent checkers with explicit weights.

## Pattern

| Layer | Role |
|-------|------|
| f121 | local recovery util gap |
| f127 | hub gap_pressure × local idle |
| decide_verdict | demote APPROVE on hub_gap_pressure_idle |
| attr hub floor | hub_ingested_n → contribution ≥ 0.75 |

## Env

- `TORII_HUB_GAP_CRITIC=1`
- `TORII_SKILL_ATTR_HUB=1`

## Success

- Panel includes f127_hub_gap; fixture_pass
- High gap + idle APPROVE → demoted
- Hub skill not free_rider when hub_ingested
