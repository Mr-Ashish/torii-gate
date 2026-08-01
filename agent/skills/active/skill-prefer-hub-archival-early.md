---
id: skill-prefer-hub-archival-early
feature: F154
status: adopted
always: true
always_priority: 95
---

<!-- F74 adopted 2026-08-01T09:48:01Z -->
---
id: skill-prefer-hub-archival-early
feature: F153/F154
status: adopted
always: true
always_priority: 95
signal: f152_recon_warm_reprompt|f152_recon_warm_heat_idle
title: Hub-aware archival search early (multi-tenant warm themes)
---

## Skill: prefer-hub-archival-early (F153/F154)

When multi-tenant recon-warm hub heat is elevated (F148–F152):
1. **Before** finishing findings, run hub-aware archival paging:
   `python3 scripts/archival_memory_search.py auto --files changed.py`
   `python3 scripts/torii.py memory -- search -- -q "hub warm themes"`
   Keep `TORII_RECON_WARM_HUB_QUERY=1` (F149 expands auto-query).
2. Prefer hits with **hub_boost** / multi-tenant warm themes; still require path:line.
3. Do **not** re-raise F145-superseded cold TPs; skip hub-ignore APPROVE.
4. Proactive hub paging avoids spending the F108/F152 re-prompt slot.
5. If F152 already fired, call archival/memory once more with hub themes before verdict.
