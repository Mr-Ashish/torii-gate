# USAGE — operational knowledge

> How to work with this part of the system.

## Common commands

- Bit 4 dry enqueue plan (no LLM spend, self-checks the payload parser): `modal run modal_app/app.py --bit 4 --repo Mr-Ashish/odoo --pr 3` → `BIT4_OK`.
- Actually enqueue the worker: append `--spawn` to the same command.
- Publish the webhook: `modal deploy modal_app/app.py`, then POST `{"repo":"Mr-Ashish/odoo","pr":3,"model":"openai/gpt-4.1-mini","post_comment":true}` to the `review_webhook` URL (or forward a GitHub `issue_comment` payload).
- F33/F34 auth: set `TORII_WEBHOOK_TOKEN` (`Authorization: Bearer …`) and/or `TORII_WEBHOOK_SECRET` (GitHub `X-Hub-Signature-256`). Fail-closed without either unless `TORII_WEBHOOK_ALLOW_OPEN=1`. Helper: `python3 scripts/webhook_auth.py sign|authorize [--allow-open]`.
- Unified trigger CLI wraps all hosts: `./scripts/trigger-review.sh print <repo> <pr>` (no spend, just prints the commands), `local` (delegates to `scripts/review-local.sh`), `modal` (bit-3 worker) — e.g. `./scripts/trigger-review.sh modal Mr-Ashish/odoo 3 --cheap --no-post`.

- Bit 1 = smoke, bit 2 = clone target repo + list PRs: `modal run modal_app/app.py [--bit 2]`.
- Enable the F39 free skip on Modal by setting `TORII_SKIP_PATH_GLOBS=docs` in the Modal app env/secret; add `TORII_SKIP_PATHS_FORCE=1` to force a skip, and `TORII_REVIEW_TIMEOUT_SECONDS` to override the 1500s review timeout.

## Debugging

- If a live POST is rejected, reproduce locally first: `python3 scripts/webhook_auth.py sign` to mint an `X-Hub-Signature-256` over the exact raw body, then `python3 scripts/webhook_auth.py authorize` to see which branch fired, rather than guessing from the Modal response.

- Modal profile version `0.6.0-f39` (F39 host parity): path-skip before clone + report-verdict after review. Quote it when comparing behaviour across deployed revisions.
- Path-skip offline: `python3 scripts/modal_parity.py path-skip --path README.md --globs docs` → exit 2 means Modal would skip OpenRouter.

- F41: `TORII_MAX_TURNS` (default 40) caps Hermes tool iterations on Modal; set `0`/`off` to disable.
- **F66** Modal is default prod live e2e host. Defaults `TORII_LENS_PACK=auto` (F63 domain packs). Optional `TORII_MEMORY_TENANT` (F65 multi-tenant hub), `TORII_HUB_PUBLISH=1` for hub ingest from Modal secrets/env.
- **F67** app version `0.8.0-f67`: live stream of orchestrator + Hermes agent.log / stderr into Modal UI logs (`print`+flush, background file tails, `TORII_STREAM_LOGS=1` tee in `run-hermes-review.sh`). Result includes `artifact_summary` + `log_streaming: true`. Traces still on volume `torii-traces`.
