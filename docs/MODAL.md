# Torii on Modal

**F66:** Modal is the **default prod live e2e host** for hub-operated reviews
(cheap bit-3 worker + optional webhook). GitHub Actions remains the doorbell
for installed target repos (`@torii review`); Modal is the kitchen for
operator-driven multi-repo scoring (milvus corpus, dogfood).

**F67:** Live log streaming into the **Modal UI**. Previously `_run(..., capture_output=True)`
hid Hermes agent activity; only a tiny `orch_*_tail` returned at the end. Now:

| Stream | Source |
|--------|--------|
| `[orch:out/err]` | `run-torii-review.sh` stage notices (line-pumped) |
| `[hermes-agent]` | live tail of `$HERMES_HOME/logs/agent.log` |
| `[hermes:err-live]` | live tail of `hermes-{pr}.stderr` (also teed by F67) |
| `[hermes-run-live]` | live tail of offset-sliced `hermes-run.log` |
| `[torii/agent-loop]` | tool_turns / tools sample after capture |
| volume | `/traces/{repo}--prN-ts/` still holds full OUT_DIR + `modal-run-index.json` |

Watch: Modal dashboard run page, or `modal app logs torii-pr-review`.

GitHub Actions = legacy doorbell + kitchen. Modal = prod kitchen (+ webhook doorbell).

## Setup (once)

```bash
pip install modal
python3 -m modal token new   # browser auth → ~/.modal.toml
```

## Bit status

| Bit | What | Verify |
|-----|------|--------|
| **1** | Skeleton app + health | `modal run modal_app/app.py` → `BIT1_OK` |
| **2** | Image git/gh + secrets + clone | `modal run modal_app/app.py --bit 2` → `BIT2_OK` |
| **3** | Manual review worker (+ F39 parity) | `modal run … --bit 3 --repo … --pr …` → `BIT3_OK` |
| **4** | Enqueue + webhook (F32) | `modal run … --bit 4` dry plan → `BIT4_OK`; deploy POST `review_webhook` |
| 5 | E2E on Mr-Ashish/odoo | real PR (paid) |

### F39 host parity (bit 3)

Modal is no longer comment-only:

1. **F38 path-skip** — if `TORII_SKIP_PATH_GLOBS` is set and every changed path matches, skip clone + Hermes; post stub + labels (`skipped_paid: true`).
2. **F36 timeout** — `TORII_REVIEW_TIMEOUT_SECONDS` (default 1500) passed into the orchestrator.
3. **F22–F37 / F9** — after a paid review, `report-verdict.sh` posts commit status, formal PR review, inline notes/suggestions, and verdict labels.

```bash
# Self-check path-skip offline
python3 scripts/modal_parity.py path-skip --path README.md --globs docs   # exit 2
# Modal secret/app env: TORII_SKIP_PATH_GLOBS=docs
```

## Commands

```bash
# Bit 1
modal run modal_app/app.py

# Bit 2 (clone Mr-Ashish/odoo + list PRs)
modal run modal_app/app.py --bit 2

# Bit 3 — cheap review worker (OpenRouter spend)
modal run modal_app/app.py --bit 3 --repo Mr-Ashish/odoo --pr 3 --model openai/gpt-4.1-mini

# Bit 4 — dry enqueue plan (no Hermes spend; parser self-check)
modal run modal_app/app.py --bit 4 --repo Mr-Ashish/odoo --pr 3
# Bit 4 — actually spawn worker
modal run modal_app/app.py --bit 4 --repo Mr-Ashish/odoo --pr 3 --spawn

# Unified CLI (also print|local)
./scripts/trigger-review.sh print Mr-Ashish/odoo 3
./scripts/trigger-review.sh modal Mr-Ashish/odoo 3 --cheap --no-post

# Deploy — public webhook URL for review_webhook
modal deploy modal_app/app.py
```

### Webhook (bit 4 + F33 auth)

POST JSON (simple API):

```json
{"repo": "Mr-Ashish/odoo", "pr": 3, "model": "openai/gpt-4.1-mini", "post_comment": true}
```

Headers when `TORII_WEBHOOK_TOKEN` is set:

```bash
curl -sS -X POST "$WEBHOOK_URL" \
  -H "Authorization: Bearer $TORII_WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"repo":"Mr-Ashish/odoo","pr":3,"model":"openai/gpt-4.1-mini"}'
```

GitHub webhook: set the same value as **Webhook secret** in GitHub and as Modal env `TORII_WEBHOOK_SECRET` (HMAC `X-Hub-Signature-256`). Accepts `issue_comment` on a PR whose body matches `@torii … review`.

| Env | Role |
|-----|------|
| `TORII_WEBHOOK_SECRET` | GitHub HMAC secret |
| `TORII_WEBHOOK_TOKEN` | Bearer / `X-Torii-Token` for simple API |
| `TORII_WEBHOOK_ALLOW_OPEN=1` | **Dev only** — permit unauthenticated when neither secret/token set |
| `TORII_WEBHOOK_DRY_RUN=1` | Plan only (no spawn) |

**F34 fail-closed:** neither secret nor token → `auth=denied` unless `TORII_WEBHOOK_ALLOW_OPEN=1`. Production **must** set at least one (fold into Modal secret `torii-github` or app env). Pure helper: `python3 scripts/webhook_auth.py sign|authorize [--allow-open]`. Handler **only spawns** `review_pr`.## Secrets

```bash
# OpenRouter (from Torii .env)
modal secret create torii-openrouter OPENROUTER_API_KEY=sk-or-…

# GitHub (PAT or `gh auth token`)
modal secret create torii-github GITHUB_TOKEN=… GH_TOKEN=…
```

## Cheap profile (default)

Modal bills **max(request, usage)** for CPU/memory. We:

| Lever | Choice |
|-------|--------|
| CPU / memory | **No reservation** (Modal min ~0.125 core) — never `cpu=2` / `memory=4096` |
| GPU | None |
| Checkout | Sparse + `--depth 1` PR head (no full Odoo clone) |
| Diff | `MAX_DIFF_BYTES=200000` |
| LLM | `openai/gpt-4.1-mini` default (not Opus) |
| Memory publish | off in Modal path (`TORII_LOCAL_PUBLISH=0`) |
| Timeout | 25 min hard kill |

```bash
# cheapest e2e
modal run modal_app/app.py --bit 3 --repo Mr-Ashish/odoo --pr 3 --model openai/gpt-4.1-mini
```

## Notes

- Pipeline scripts under `scripts/` stay the product SoT.
- Do not run Hermes inside the webhook HTTP handler — always `spawn`.
- Fat traces → Modal Volume / object storage (not Actions artifacts).
- **F31:** `review_pr` sets `TORII_HOST=modal`; orchestrator writes `run-bundle.json` under `.torii-out` (and the volume copy). Return dict includes `run_bundle` path when present.
