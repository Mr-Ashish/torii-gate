# Torii Gate architecture

Torii is a **security-first product brand** on the same control-plane architecture as the Luffy PR review agent (internal substrate).

## Source of truth (patterns reused)

Local parent: `~/Documents/experiments/pr-review-agent`  
Upstream: https://github.com/Mr-Ashish/luffy-pr-review-agent

| Layer | Reused as-is (rebranded) | Torii product default |
|-------|--------------------------|------------------------|
| Orchestrator | `scripts/run-torii-review.sh` | Security pack + labels on |
| Context | `assemble-context.sh` | Sparse PR paths, capped diff |
| Agent | Hermes + OpenRouter | `agent/config.yaml` |
| Memory | `.torii/` local + optional hub | FP resolve memory |
| Traces | redacted fat traces | CI artifacts |
| GitHub | `torii-pr-review.yml` | `@torii review this pr` |
| Packs | `agent/packs/*` | **`security` default** |
| Labels | `apply-verdict-labels.py` | prefix `torii` |

## Pipeline

```
PR comment / dispatch
  → association + cooldown
  → assemble context (diff, SOUL, MEMORY, security pack)
  → Hermes agent loop + tools
  → normalize review
  → distill memory + FP update
  → post comment / labels / status
  → save redacted trace
```

## Product modules (roadmap)

1. **Torii Gate** (now) — PR/CI security gate  
2. **Torii Trust** — SARIF → agent validator  
3. **Torii Plane** — coding-agent policy control plane  

## Env / secrets

See `.env.example`. Required: `OPENROUTER_API_KEY`.  
GitHub Actions: same secret + optional model/cost vars with `TORII_` prefix.
