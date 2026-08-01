# F121 research note — Recovery skill utilization critic

**Date:** 2026-08-01  
**Fire:** F121

## Sources

1. Mem2Act / F105: inject ≠ utilization — score tool calls.
2. SkillsBench: curated skills help only when applied, not merely present.
3. SoK Agentic Skills (arXiv 2602.20867): skill quality vs availability.
4. Torii F119/F120: always inject recovery skills; no post-run check they fired.

## Pattern

| Layer | Role |
|-------|------|
| skill-router.json | selected + always_selected + inject_chars + f120 saved |
| skill-hits.json | tool_hit per recovery skill |
| util score | util_rate = tool_hits / recovery_injected; gap if 0 tools |
| F78 panel | f121_recovery_util checker (weight 0.08) |
| demote | APPROVE + gap → COMMENT (`recovery_skill_idle_no_tool_hit`) |

## Commands

```bash
python3 scripts/skill_router.py util --out-dir "$OUT_DIR"
```

## Success

- Offline: util_ok; gap true on idle product-cli; inject_chars ≥ 1
- Critic demotes APPROVE when recovery idle
- Modal BIT3_OK; recovery-skill-util.json in traces when wired
