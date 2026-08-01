# F124 research note — Federate recovery util + doctor recovery_ok

**Date:** 2026-08-01  
**Fire:** F124

## Sources

1. FederatedSkill / F77/F116: share skill themes not trajectories.
2. Multi-tenant privacy: tenant hash only; no paths/commands.
3. Loop-eng doctor: day-2 habit must surface recovery readiness.

## Pattern

| Layer | Role |
|-------|------|
| util | F121 recovery-skill-util.json |
| federate_recovery_util | signals: tool hit per skill id + gap/ok bins |
| privacy | skill_id + util_rate_bin + inject_chars_bucket + tenant_hash |
| doctor | skill_loop scorecard.recovery_ok required for doctor_pass |

## Env

- `TORII_RECOVERY_UTIL_FEDERATE=1` (default)

## Success

- Fixture fed_ok + privacy_ok; doctor recovery_ok true
- No `/Users/` or raw tenant strings in signals
