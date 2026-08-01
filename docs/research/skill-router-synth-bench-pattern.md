# F160 research note — Skill-router synth for bench util measurement

**Date:** 2026-08-01  
**Fire:** F160

## Sources

1. Live F155–F159: recovery_injected_n=0 on insecure-demo bench because skill-router.json missing.
2. SkillsBench: measure genuine skill utilization requires knowing what was injected.
3. Assay: idle always skills invisible if inject set is empty.

## Gap

`bench_security_gate live` skips assemble-context. Inject only writes skill-router.json when OUT_DIR is set during assemble. Util then sees empty always_selected → F121–F159 never fire on the primary live path.

## Pattern

| Layer | Role |
|-------|------|
| ensure_skill_router_doc | load or synthesize always skills |
| score_recovery_util | uses synth when artifact missing |
| inject_into_prompt | write artifact next to prompt.md parent |
| bench live | skill_router inject before hermes |

## Success

- Fixture f160_ok: synth always recovery inject ≥2; hub_archival_util_gap true
- Live: skill-router.json present; recovery_injected_n>0 when always skills active
