# Agent design split — tool vs code vs prompt vs MD

**Updated:** 2026-08-01 (F62)  
**Principle:** deterministic work → scripts; judgment → lean prompts; persona/lenses → MD; config → toggles.

| Feature | Code / scripts | Prompt / intelligence | MD / agent files | Toggles / config |
|---------|----------------|----------------------|------------------|------------------|
| F9/F9b/F9c inline | `post-inline-comments.py` anchor map, suggestion blocks | severity which findings matter | SOUL path:line discipline | `inline_comments`, `inline_suggestions`, `inline_max` |
| F54 fix-it | `format_fixit_prompt` packing | — (template is code) | — | `fixit_prompts` |
| F53 issue ctx | `linked_issue_context.py` extract/fetch/pack | how issues change review judgment | review-prompt section header | `issue_context`, `issue_from_branch`, max ints |
| F52 multi-lens | `normalize-review.py` section alias | multi-lens table fill | review-prompt + SOUL checklist | (recipes backlog → packs) |
| F50 severity | `severity_calibration.py` | model-assigned severity | SOUL scale | `severity_calibration` |
| F45/F49 tool turns | gate + reprompt scripts | whether re-ask is needed | — | `tool_turns_gate`, `tool_turns_reprompt` |
| F55 toggles | **`feature_toggles.py` registry + resolve** | none | DEV.md split note | `.torii/toggles.json` + env |
| Federated memory | publish/ingest I/O + F62 FP section | light apply of FP patterns | MEMORY.seed + `## FP patterns` | `hub_publish`, `local_publish`, `fp_resolve` |
| F60 reply on thread | `reply_on_thread.py` match+`in_reply_to` | — | inline markers | `reply_on_thread` |
| Mermaid / filler / incremental / testplan | scripts first (F57–F61) | judgment only where needed | thin recipes | new registry entries |
| F61 testplan generation | `testplan_generation.py` files+diff→P0/P1/P2 cases | refine / drop-with-reason | `### Suggested test plan` | `testplan`, `testplan_max_cases` |
| F62 FP resolve + memory | `fp_resolve_memory.py` classify/mine/merge | re-raise only with new evidence | MEMORY `## FP patterns` + review-prompt | `fp_resolve`, `fp_resolve_max` |
| F63 domain packs + auto | `lens_recipes.py` path_globs score + milvus/go/cpp JSON | fill ok/concern per pack hints | `agent/packs/*.json` | `lens_pack=auto` default |
| F64 durable FP rules | `fp-rules.json` load/save + hub-ingest merge | same as F62 | `.torii/fp-rules.json` | `TORII_FP_RULES_FILE` |

## Hermes boundary (research note)

Hermes: tools are discrete callable capabilities; workflows that parse/gate/pack
must not be re-encoded as long prompt spaghetti. Torii mirrors this: orchestrator
shell + Python for gates; SOUL/review-prompt for persona and lens judgment only.
Never fork Hermes into Torii — adopt patterns (toolsets, pin, memory file).
