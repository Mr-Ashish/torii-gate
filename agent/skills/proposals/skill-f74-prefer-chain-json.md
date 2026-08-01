---
id: skill-f74-prefer-chain-json
feature: F74
status: proposal
source: feedback:chain JSON absent; inferred from path+theme
weak_dims: feedback
created_at: 2026-08-01T00:23:52Z
title: Prefer chain JSON over inference (fitness feedback)
---

## Skill: prefer-chain-json (F74 fitness-gated)

When taint-candidates.json or chain revalidate output exists:
1. Align findings with **candidate source/sink pairs** rather than free-form inference.
2. Quote or paraphrase the candidate rule id when it matches.
3. If no candidate matches a claim, label confidence **unvalidated**.
