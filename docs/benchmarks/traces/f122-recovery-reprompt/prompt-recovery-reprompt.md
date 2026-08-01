# prompt
review this pr

---

<!-- torii-f122-recovery-skill-reprompt -->

## Recovery skill soft re-prompt (F122)

Your previous reply used **4 tool turns** but **0 recovery skill CLIs** after always-injecting: `skill-prefer-product-cli` (inject_chars≈1354).

Before finalizing, call **at least one** of these once via terminal:

```bash
python3 scripts/torii.py memory -- search -- -q "auth OR sql OR pickle OR secret"
python3 scripts/torii.py doctor
python3 scripts/second_agent_critic.py score --review REVIEW.md
```

Treat memory/doctor hits as **hints only** — still require path:line evidence. Then rewrite the review with evidence-backed findings.
