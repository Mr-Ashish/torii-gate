# F158 research note — Hub-archival util fitness demote/boost

**Date:** 2026-08-01  
**Fire:** F158

## Sources

1. SkillsBench (arXiv 2602.12670): measure genuine skill utilization, not inject alone.
2. Agent skill evaluation survey (arXiv 2606.11435): longitudinal fitness; drop skills that never contribute.
3. Assay: idle/negative skills must be suppressed after evidence.
4. Torii F116 tool shield + F126 hub recovery fitness; F155–F157 util/reprompt/critic for hub-archival.

## Gap

Per-run util (F155) and re-prompt/critic (F157/F156) do not compound into durable fitness. Chronic hub_archival inject≠hub_boost left the always skill un-penalized across PRs.

## Pattern

| Layer | Role |
|-------|------|
| ingest_hub_archival_util | selected_n++ / hit or gap counters |
| apply_demotions F158 | gap_rate≥0.67 after min_n → demote; tool hit revive |
| fitness_boosts | util_rate boost − gap_rate penalty |
| cycle | score util before demote |
| federate | hub_archival/f158 tags on tool-hit skills |

## Success

- Fixture f158_ok: gap demote → hit revive → boost delta → fed tags
- skill_loop hub_archival_fitness_ok
