# F84 research note — progressive skill router + hit scoring

**Date:** 2026-08-01  
**Fire:** F84

## Sources

1. **Progressive disclosure** (Claude Skills / Simon Willison / HN): compact index of all skills; full body only for relevant verticals — prevents context overload.
2. **Vercel agent evals**: in ~56% of cases skills were never invoked when available as dump-only context; routing + measurement required.
3. **FederatedSkill** (arXiv 2606.03143): collaborative skill evolution via privacy-safe themes — Torii emits `federated_skill_themes` (skill ids that hit), not full skill text or paths.
4. Prior Torii: F69 injects up to 8 full skills; F82 auto-adopts into active/ — no path relevance or post-run hit rate.

## Pattern

| Idea | Torii F84 |
|------|-----------|
| Index + selective load | `skill_router inject`: index all + full bodies for top-K by path themes |
| Path/theme routing | EXT_THEMES + skill frontmatter/DEFAULT_TRIGGERS; always-on core skills |
| Measure invocation | `score` keyword/title hits in review → skill-hits.json |
| Privacy federation | skill ids only in federated_skill_themes |
| Replace bulk dump | TORII_SKILL_ROUTER_REPLACE strips F69 block when router injects |

## Success metric

- Offline fixture: py paths select f74 security skills + always; good hit_rate > weak; privacy_ok
- Live: SKILL_ROUTER=1 in meta; skill-router.json + skill-hits.json in out_dir
