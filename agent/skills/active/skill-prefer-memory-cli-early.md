<!-- F113 dual-gate adopted 2026-08-01T04:53:53Z -->
<!-- F114 always-on + tool-outcome scored -->
---
id: skill-prefer-memory-cli-early
feature: F112/F113/F114
status: adopted
always: true
signal: f106_recovered|memory_utilization_gap
created_at: 2026-08-01T04:47:50Z
title: Call torii product/memory CLI early mid-review
---

## Skill: prefer-memory-cli-early (F112/F113)

When memory sections are injected (F103 CLI / F98 archival / F100 graph / F70 TP):
1. **Before** finishing findings, call the product front door once:
   `python3 scripts/torii.py memory -- help`
   `python3 scripts/torii.py memory -- search -- -q "auth OR sql OR pickle OR secret"`
   or `python3 scripts/torii_memory.py search -- -q "theme keywords"`
2. Prefer **search/graph** on changed basenames (F100 multi-hop) before re-raising old themes.
3. Treat hits as **hints only** — still require path:line evidence to block.
4. Do not wait for a soft re-prompt (F106) — proactive use scores higher (F105 utilization).
5. Soft re-prompts share a budget (F108); early use avoids spending the only recovery slot.
