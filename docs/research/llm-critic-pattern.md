# F81 research note — optional LLM checker atop F78

**Date:** 2026-08-01  
**Fire:** F81

## Sources

1. QASecClaw: LLM validation agent after SAST/discovery.
2. VulAgent: separate confirmation agent.
3. Torii F78: deterministic panel; open gap was optional semantic pass.

## Pattern

| Layer | Role |
|-------|------|
| F78 | Default free checker panel |
| F81 | Optional OpenRouter JSON-only critic |
| Schema gate | Normalize verdict/confidence; soft-skip on fail |
| Privacy | Redact keys/paths before API |

Default **off** (`TORII_LLM_CRITIC=0`).
