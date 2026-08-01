# F79 research note — workflows-as-code + install UX

**Date:** 2026-08-01  
**Fire:** F79

## Sources

1. Loop Engineering: loops as explicit, validated artifacts + readiness scorecards.
2. Agent/CI pipelines as declarative graphs (stages, soft-fail, entries).
3. Product gap: pack install omitted F70–F78 intelligence scripts; no capability matrix for adopters.

## Pattern

| Idea | Port |
|------|------|
| Declarative workflow | `docs/workflows/torii-gate.workflow.yaml` |
| Validate readiness | L0–L3 from script existence |
| Install UX deep link | `install-guide` capability matrix |
| Pack completeness | `pack_scripts` ⊆ `RUNTIME_SCRIPTS` |

## Success metric

- fixture L3 100%; pack-check install_lists_all; smoke F79 green
