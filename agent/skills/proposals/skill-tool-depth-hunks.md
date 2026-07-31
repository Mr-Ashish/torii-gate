---
id: skill-tool-depth-hunks
feature: F69
status: proposal
signal: zero_tools|f49_recovered
created_at: 2026-07-31T19:23:40Z
title: Tool depth: prefer diff hunks over file heads
---

## Skill: tool-depth-hunks (F69)

When reviewing multi-file code PRs:
1. Open the unified **diff file** first for exact `+/-` hunks.
2. Use `rg -n SYMBOL path` then `sed -n 'START,ENDp'` — never stop at `head`.
3. At least one tool must target a **changed region or symbol**.
4. If tools fail, say so; do not APPROVE on incomplete evidence.
