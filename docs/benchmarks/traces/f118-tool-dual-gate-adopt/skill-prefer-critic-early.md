<!-- F118 dual-gate tool-attr adopted -->
<!-- F74 adopted 2026-08-01T05:36:49Z -->
---
id: skill-prefer-critic-early
feature: F117/F118
status: adopted
signal: f117_critic_tools
created_at: 2026-08-01T05:35:12Z
title: Run second-agent critic path evidence early
---

## Skill: prefer-critic-early (F117)

When dual-pass critic tooling is available:
1. After draft findings, run:
   `python3 scripts/second_agent_critic.py score --review REVIEW`
2. Demote APPROVE claims without path:line; boost full_chain themes.
3. Do not self-approve unvalidated narrative — checker is independent.

