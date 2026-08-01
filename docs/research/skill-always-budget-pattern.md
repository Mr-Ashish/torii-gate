# F119 research note — Always-on skill budget with recovery priority

**Date:** 2026-08-01  
**Fire:** F119

## Sources

1. **SkillReducer** (arXiv 2603.29919): skill injection is a context cost; unbounded always-on is skill bloat.
2. **Agent Skills progressive disclosure**: index all, load full body only when needed.
3. **Torii F114–F118**: memory/product/critic recovery skills need full body to teach tool calls — but max_full=4 was already filled by soft always (tool-depth, preserve).

## Gap

After F118, product-cli and critic were active but `always=false`, so selection kept memory + tool-depth + preserve + one security skill — **product-cli never full-body injected**.

## Pattern

| Layer | Role |
|-------|------|
| always candidates | memory (100), product-cli (90), critic (85), tool-depth (50), preserve (40) |
| ALWAYS_MAX | default 3 slots |
| deferred | always losers compete on theme score (no 1000 boost) |
| max_full | remaining slots for path-matched security skills |

## Env

- `TORII_SKILL_ROUTER_ALWAYS_MAX=3`
- `TORII_SKILL_ROUTER_ALWAYS_PRIO=id:prio,...`

## Success

- Offline fixture: memory+product always_selected; tool-depth deferred; product_in_py
- Live Modal BIT3_OK with product-cli in prompt when always budget holds
