<!-- F113/F114/F119/F120 compact recovery skill -->
---
id: skill-prefer-memory-cli-early
feature: F112/F113/F114/F120
status: adopted
always: true
always_priority: 100
signal: f106_recovered|memory_utilization_gap
title: Call torii product/memory CLI early mid-review
---

## Skill: prefer-memory-cli-early

1. Before finishing findings, call:
   `python3 scripts/torii.py memory -- search -- -q "auth OR sql OR pickle OR secret"`
   or `python3 scripts/torii_memory.py search -- -q "theme keywords"`
2. Prefer search/graph on changed basenames before re-raising old themes.
3. Treat hits as hints only — still require path:line evidence to block.
4. Do not wait for F106 re-prompt — early use saves the F108 recovery budget.
