# Review

---

<!-- torii-f122-recovery-skill-reprompt -->

## Hub-archival recovery soft re-prompt (F157)

Your previous reply used **3 tool turns** but recovery skill CLIs remain idle for: `skill-prefer-hub-archival-early` (inject_chars≈0).

**F157 hub-archival util gap:** call `archival_memory_search` with hub warm themes so `hub_boost` evidence appears (generic memory CLI is not enough).

Before finalizing, call **at least one** of these once via terminal:

```bash
python3 scripts/torii.py memory -- search -- -q "auth OR sql OR pickle OR secret"
python3 scripts/archival_memory_search.py auto  # hub warm / hub_boost (F155)
python3 scripts/torii.py doctor
python3 scripts/second_agent_critic.py score --review REVIEW.md
```

Treat memory/doctor hits as **hints only** — still require path:line evidence. Then rewrite the review with evidence-backed findings.
