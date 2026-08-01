# F150 research note — Recon-warm hub ignore → critic demote

**Date:** 2026-08-01  
**Fire:** F150

## Sources

1. F127/F139/F143 hub gap critic: multi-tenant pressure + local idle → demote APPROVE.
2. F148/F149 recon-warm federate + hub query expand.
3. Loop-eng maker/checker: federation without enforcement is dashboard theater.

## Gap

Hub warm themes can expand archival query (F149) but a run can still soft-disable hub query / zero boost and APPROVE. Multi-tenant retrieval heat must demote weak APPROVE.

## Pattern

| Layer | Role |
|-------|------|
| post_score + signals | heat / multi-tenant theme_n |
| archival-search.json | local hub_boost_n / hub_themes |
| f150 checker | high heat + local_idle → ok=False |
| decide_verdict | APPROVE → COMMENT |

## Success

- Fixture f150_ok; test demotes APPROVE
- Inject brief lists F150
