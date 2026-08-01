# F134 research note — Federate scorecard skills + fitness blend

**Date:** 2026-08-01  
**Fire:** F134

## Sources

1. FederatedSkill: skill themes as multi-tenant unit.
2. Hermes FitnessScore multi-dim blend.
3. F133 adopt without federate/fitness leaves ops skills local-only.

## Pattern

| Layer | Role |
|-------|------|
| active scorecard skills | list_active_scorecard_skills |
| federate | scorecard-skill-signals.json |
| hub ingest | privacy-safe summary only |
| trajectory fitness | ops_bonus → procedure/tool |

## Success

- privacy_ok; no raw tenant; no `/Users/`
- fitness signals include f134_ops_bonus when brand_ready
