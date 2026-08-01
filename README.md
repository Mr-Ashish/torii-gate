# Torii Gate

**The security gate for every pull request.**  
*Nothing ships without crossing the gate.*

Agent-powered PR/CI **security merge authority**: path-evidenced findings, maker/checker critics, compound memory, measured skill loop. Built for AI-written and human code.

[![Torii Gate](https://img.shields.io/static/v1?label=trigger&message=%40torii+review+this+pr&color=C9A227&style=for-the-badge)](#trigger)
[![pack](https://img.shields.io/static/v1?label=default+pack&message=security&color=0B0F19&style=for-the-badge)](agent/packs/security.json)
[![provider](https://img.shields.io/static/v1?label=provider&message=OpenRouter+%2B+Hermes&color=C41E3A&style=for-the-badge)](#stack)

## Why Torii

Most AI PR bots optimize for *code quality comments*. Torii optimizes for **security merge authority**:

- Injection, authz, secrets, XSS/CSRF, SSRF, path traversal, unsafe deserialize, crypto misuse  
- Evidence from workspace tools (not invented vulns)  
- Durable `.torii/` memory so false positives die twice  
- Labels + optional required checks as the **gate**  
- **Skill compound loop** so the gate gets *stricter and quieter* over time — not noisier  

```text
route → hit → fitness → dual → attr → inject
```

Skills that do not contribute do not ship in the next prompt. See [`PRODUCT.md`](PRODUCT.md) (ICP + mental models) and [`docs/brand/`](docs/brand/).

## Trigger

```text
@torii review this pr
@torii review
```

Or: **Actions → Torii Gate → Run workflow** (PR number).

## Quick start (this repo)

```bash
cp .env.example .env   # set OPENROUTER_API_KEY
# optional: copy keys from sibling Luffy checkout
# cp ../pr-review-agent/.env .env

# Offline product smoke (no API key)
./scripts/smoke-torii-gate.sh

# Local full review (needs gh + PR access + OPENROUTER_API_KEY)
export REPO=owner/repo PR_NUMBER=1
./scripts/run-torii-gate.sh
```

Dogfood app with intentional vulns: [`demo/insecure/`](demo/insecure/). Gate contract: [`docs/GATE.md`](docs/GATE.md).

Install on a **target** repo: copy workflow pack or point `torii_repository` at this hub (see `pack/`).

## Live e2e (Modal)

```bash
python3 scripts/modal_secrets_bootstrap.py apply   # once
modal run modal_app/app.py --bit 3 --repo owner/name --pr N \
  --model deepseek/deepseek-v4-pro --no-post-comment
# optional semantic checker:
modal run modal_app/app.py --bit 3 --repo owner/name --pr N --llm-critic --no-post-comment
```

Hermes logs stream to the Modal UI (F67). Skills evolve offline with regression gates (F82).

## Stack (reused control plane)

| Piece | Role |
|-------|------|
| GitHub Actions | Trigger + runner |
| Hermes Agent | Tool-calling review loop |
| OpenRouter | Model routing |
| `.torii/` | Repo-local memory |
| Security pack | Default lens recipe |
| Fat traces | Audit artifacts (redacted) |

Architecture details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Brand: [docs/brand/TORII.md](docs/brand/TORII.md)

## Product roadmap

| Module | Status |
|--------|--------|
| **Torii Gate** | Building now |
| **Torii Trust** | SARIF → agent validator (next) |
| **Torii Plane** | Coding-agent policy plane (vision) |

## Env

| Var | Purpose |
|-----|---------|
| `OPENROUTER_API_KEY` | Required |
| `TORII_MODEL` | Model override |
| `TORII_LENS_PACK` | Default `security` |
| `TORII_MAX_TURNS` | Hermes turn cap (default 40) |
| `TORII_MAX_COST_USD` | Soft spend cap |
| `TORII_PR_LABELS` | Verdict labels (default on) |

Full list: `.env.example`.

## License

MIT (same lineage as the Luffy control-plane substrate).

## Hub71 Access

Application pack and decision materials: **[docs/hub71/](docs/hub71/)**  
Paste-ready answers: **[docs/hub71/ACCESS-APPLY.md](docs/hub71/ACCESS-APPLY.md)**
