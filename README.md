# Torii Gate

**The security gate for every pull request.**  
*Nothing ships without crossing the gate.*

**Primary story:** the gate gets *stricter and quieter* over time — not noisier.

Agent-powered PR/CI **security merge authority**: path-evidenced findings, maker + checker, skills and memory that compound. Built for AI-written and human code.

[![Torii Gate](https://img.shields.io/static/v1?label=trigger&message=%40torii+review+this+pr&color=C9A227&style=for-the-badge)](#trigger)
[![pack](https://img.shields.io/static/v1?label=default+pack&message=security&color=0B0F19&style=for-the-badge)](agent/packs/security.json)
[![provider](https://img.shields.io/static/v1?label=provider&message=OpenRouter+%2B+Hermes&color=C41E3A&style=for-the-badge)](#stack)

## How Torii works (buyer)

One diagram — full write-up: [`docs/brand/BUYER-DIAGRAM.md`](docs/brand/BUYER-DIAGRAM.md).

```text
  PR / CI ──► TORII GATE ──► merge signal (torii/gate)
                 │
     1. REVIEW + CHECK     tools on the diff; demote empty APPROVE
     2. COMPOUND           skills that measure in · memory that pages in
     3. MERGE SIGNAL       required check · labels · comment
                 │
                 ▼
        next PR is quieter and sharper
```

Most AI PR bots optimize for *code quality comments*. Torii optimizes for **security merge authority**:

- Injection, authz, secrets, XSS/CSRF, SSRF, path traversal, unsafe deserialize, crypto misuse  
- Evidence from workspace tools (not invented vulns)  
- Durable `.torii/` memory so false positives die twice  
- Labels + required check **`torii/gate`** as the merge signal  
- Every run teaches the next — stricter blocks, less noise  

**CLI front door:** `python3 scripts/torii.py help` · `status --text` · `doctor` · `ops -- status` · `enterprise -- status` · `memory -- search`

**Measured dogfood (honesty):** live Modal + Hermes on open-source PRs (`POST_COMMENT=0`) — **~90s** time-to-signal p50 · **~$0.01** cost/PR p50 · gate certificates with reason codes. Not slogans: [`docs/ops/cost-pr-dashboard.md`](docs/ops/cost-pr-dashboard.md) · [`docs/benchmarks/golden-path-metrics.md`](docs/benchmarks/golden-path-metrics.md) · landing source: [`docs/brand/landing.html`](docs/brand/landing.html) · **deployed landing (GitHub Pages):** [mr-ashish.github.io/torii-gate](https://mr-ashish.github.io/torii-gate/) (`python3 scripts/build_landing_site.py build`).

Buyer brief: [`PRODUCT.md`](PRODUCT.md) · brand: [`docs/brand/`](docs/brand/) · Advanced loop detail (engineers): PRODUCT → **Advanced**.

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

# Offline product smoke (no API key) — also CI: smoke-offline.yml
./scripts/smoke-torii-gate.sh
python3 scripts/ops_dashboard.py report   # cost/PR + fail-closed dashboard

# Local full review (needs gh + PR access + OPENROUTER_API_KEY)
export REPO=owner/repo PR_NUMBER=1
./scripts/run-torii-gate.sh
```

Dogfood app with intentional vulns: [`demo/insecure/`](demo/insecure/). Gate contract: [`docs/GATE.md`](docs/GATE.md).

### Golden path (target repo → required check)

**Buyer loop:** install → require status **`torii/gate`** → `@torii review this pr` → metrics.

```bash
./scripts/install-torii.sh /path/to/your-app           # or --minimal for 5-min surface
# multi-org fleet (optional enterprise light):
# ./scripts/install-torii.sh --tenant acme-platform /path/to/your-app
# then: secret OPENROUTER_API_KEY · branch protection requires torii/gate
python3 scripts/torii.py status --text                 # day-2 one-screen (cost · cert · quieter · fail-closed)
python3 scripts/torii.py doctor                        # day-2 habit (one CLI)
python3 scripts/golden_path_metrics.py report          # → docs/benchmarks/golden-path-metrics.md
```

**5-minute install:** [`docs/INSTALL.md`](docs/INSTALL.md) · golden path: [`docs/GOLDEN-PATH.md`](docs/GOLDEN-PATH.md) · metrics: [`docs/benchmarks/golden-path-metrics.md`](docs/benchmarks/golden-path-metrics.md).

### Product surfaces (one CLI)

Day-one path stays install → require **`torii/gate`** → first review. Everything below is the same product, discoverable without research F-IDs:

| Surface | Doc | Command |
|---------|-----|---------|
| Install / doctor | [`docs/INSTALL.md`](docs/INSTALL.md) | `python3 scripts/torii.py doctor` · `status --text` |
| Golden path + cost/PR | [`docs/GOLDEN-PATH.md`](docs/GOLDEN-PATH.md) · [`docs/ops/cost-pr-dashboard.md`](docs/ops/cost-pr-dashboard.md) | `python3 scripts/torii.py golden-path -- status` · `ops -- status` |
| Ops fail-closed | [`docs/ops/RELIABILITY.md`](docs/ops/RELIABILITY.md) | tool-turns gate on · smoke CI · `ops -- status` |
| Gate certificate | [`docs/GATE.md`](docs/GATE.md) | `python3 scripts/torii.py certificate -- fixture` |
| Quieter over time | [`docs/QUIETER.md`](docs/QUIETER.md) | `python3 scripts/torii.py quieter -- status` |
| Tool-use quality | [`docs/TOOL-USE.md`](docs/TOOL-USE.md) | `python3 scripts/torii.py tool-use -- status` |
| Workflows-as-code | [`docs/WORKFLOWS.md`](docs/WORKFLOWS.md) | `python3 scripts/torii.py workflow -- scorecard` |
| Memory (FP die twice) | [`docs/MEMORY.md`](docs/MEMORY.md) | `python3 scripts/torii.py memory -- doctor` |
| Federation | [`docs/FEDERATION.md`](docs/FEDERATION.md) | `python3 scripts/torii.py federation -- status` |
| Self-evolution (day-2) | [`docs/SELF-EVOLVE.md`](docs/SELF-EVOLVE.md) | `python3 scripts/torii.py self-evolve -- status` |
| Enterprise light | [`docs/enterprise/`](docs/enterprise/) · install `--tenant` | `python3 scripts/torii.py enterprise -- status` |
| **Commercial rollup** | [`docs/benchmarks/commercial-scorecard.md`](docs/benchmarks/commercial-scorecard.md) | `python3 scripts/torii.py commercial -- status` |
| **Pricing (open core)** | [`docs/PRICING.md`](docs/PRICING.md) | Open Gate free · Team · Business · Enterprise roadmap |

**Public labeled eval** (Juice Shop + NodeGoat + Django/Flask themes, fixed **seed 42**, model pin, freshness badge):  
[`docs/benchmarks/public-eval/SCORECARD.md`](docs/benchmarks/public-eval/SCORECARD.md) · [`BADGE.md`](docs/benchmarks/public-eval/BADGE.md) · `python3 scripts/public_eval.py report` · `status` (age_hours / freshness_ok)

Install on a **target** repo: copy workflow pack or point `torii_repository` at this hub (see `pack/`).

## Live e2e (Modal)

```bash
python3 scripts/modal_secrets_bootstrap.py apply   # once
modal run modal_app/app.py --bit 3 --repo owner/name --pr N \
  --model deepseek/deepseek-v4-pro --no-post-comment
# optional semantic checker:
modal run modal_app/app.py --bit 3 --repo owner/name --pr N --llm-critic --no-post-comment
```

Hermes logs stream to the Modal UI. Skills evolve offline with dual-gate adopt (see [`docs/SELF-EVOLVE.md`](docs/SELF-EVOLVE.md)).

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
