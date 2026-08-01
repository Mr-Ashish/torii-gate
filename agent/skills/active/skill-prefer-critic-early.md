<!-- F118/F119/F120 compact recovery skill -->
---
id: skill-prefer-critic-early
feature: F117/F118/F120
status: adopted
always: true
always_priority: 85
signal: f117_critic_tools
title: Run second-agent critic path evidence early
---

## Skill: prefer-critic-early

1. After draft findings, run:
   `python3 scripts/second_agent_critic.py score --review REVIEW`
2. Demote APPROVE claims without path:line; boost full_chain themes.
3. Do not self-approve unvalidated narrative — checker is independent.
