# DEV — engineering knowledge

> How this part of the system is built.

## Architecture

- This repo doubles as the central hub: every target repo's run is ingested under `memory/repos/{owner}--{repo}/` (slug uses `--` to flatten owner/repo), holding `MEMORY.md`, `latest.json`, and a `runs/` history.
- Publish path: `build-hub-payload.py` produces a redacted, size-capped payload → `publish-run-to-hub.sh` (direct push by default, `repository_dispatch torii-run` optional) → `hub-ingest-run.py` commits under `memory/`.
- Hub memory is preloaded into `HERMES_HOME` at the start of each run (`preload-hub-memory.sh`), which is what makes the next review on the same repo smarter — memory is cross-run and cross-repo, not per-job.
- Hub behaviour is env-configurable per target repo: `TORII_HUB_REPO` (default `Mr-Ashish/torii-gate`), `TORII_HUB_MODE` (`direct`|`dispatch`|`both`), `TORII_HUB_PUBLISH=0` to disable.

- **F28 repo-local memory is now the default store:** each target repo owns `.torii/` on its default branch (`MEMORY.md`, `latest.json`, `runs/{safe_trace}/{meta.json,review.md,summary.md}`); the hub `memory/repos/{slug}/` tree becomes an opt-in second copy, not the system of record.
- `scripts/hub-ingest-run.py` is now dual-layout via `TORII_INGEST_LAYOUT`: `hub` (default, `HUB_ROOT/memory/repos/{owner}--{repo}`) or `local` (`TORII_MEMORY_ROOT/$TORII_MEMORY_PATH`, default `.torii`). Shared body is `write_run_pack()`; `slug=None` is the sentinel that means "local layout" and drives both `meta.layout` and the relative `run_path` in `latest.json`.
- Only the hub layout maintains `memory/index.json` (`update_hub_index()`); a local-layout ingest deliberately writes no cross-repo index.
- Pipeline order in `run-torii-review.sh`: `preload_memory` → … → `save-trace` (fat Actions artifact) → `publish_local` (`scripts/publish-run-local.sh`, always) → `publish_hub` (opt-in). Fat traces stay artifacts; only the slim pack enters git.

## Pitfalls

- Direct push therefore needs write on the hub: on the hub repo itself `GITHUB_TOKEN` + `contents: write` is sufficient (self-review), but any *other* target repo requires `TORII_HUB_TOKEN` (PAT with contents write on the hub) or hub publishing silently degrades.
- Original failure mode this layer exists to fix: hub memory was written after a run but **not loaded into** the next review — the preload step is the load half of the contract, and without it the `memory/` tree is write-only.

- `preload-hub-memory.sh` fetches `.torii/MEMORY.md` through the **default-branch contents API** (`api.github.com/repos/$REPO/contents/...`), not from the checked-out workspace: the PR checkout is sparse/PR-head, so reading it from disk would miss or stale the memory. Consequence: memory committed only on a PR branch is invisible until it lands on the default branch.
- Preload is strictly first-hit-wins — local success exits immediately and never merges hub memory on top; hub is tried only when `HUB_OK=1` (mode `hub|both` or `TORII_HUB_PUBLISH=1`). Diagnose via the emitted `MEMORY_SOURCE=local|hub|missing|seed` line (legacy `HUB_MEMORY=` is kept for compatibility but now also carries `local`/`skipped`).
- Local-layout ingest resolves `TORII_MEMORY_PATH` against `TORII_MEMORY_ROOT` and refuses paths that escape the root (`startswith` check) — a `../` value fails the run rather than writing outside the checkout.
- `trace_id` is sanitized (`[^A-Za-z0-9._-]+` → `-`) before it becomes a `runs/` directory name, so trace dir names on disk can differ from the `trace_id` recorded in `latest.json`/`meta.json`.
- The pipeline stage was renamed `preload_hub_memory` → `preload_memory`; anything parsing stage names out of `timings.json` (dashboards, showcase docs) needs updating.

## Design decisions

- Memory routing is one var: `TORII_MEMORY_MODE` = `local` (default) | `hub` | `both`, plus `TORII_MEMORY_PATH` (default `.torii`). Both `preload-hub-memory.sh` and `publish-run-to-hub.sh` lowercase the mode before matching, and `run-torii-review.sh` exports defaults so local invocations behave like CI.
- Hub on/off precedence is deliberate and duplicated on both halves: an explicit `TORII_HUB_PUBLISH` (`1`/`0`) always wins; when unset, mode `hub|both` implies publish=1 and anything else implies publish=0. This flips the old `TORII_HUB_PUBLISH:-1` default to off without changing the var's meaning.
- The reusable workflow `unset`s `TORII_HUB_PUBLISH` when the GitHub Actions variable is empty, because an empty-string var would otherwise defeat the scripts' `:-` mode-based defaulting — same pattern already used for empty `TORII_MODEL` (F26).
- `publish-run-local.sh` is added to `RUNTIME_SCRIPTS` in `install-torii.sh` and is invoked on the config-error path too (before `publish-run-to-hub.sh`), so failed runs still leave a local record.

- **F42:** `run-hermes-review.sh` may select cheap vs full model via `scripts/model_tier.py` when `TORII_MODEL_TIER=auto` (docs/tiny → cheap). Does not change SOUL/prompt content.

- **F43:** preflight cost may skip Hermes or force cheap model when `TORII_MAX_COST_USD` is tight — SOUL/prompt unchanged; stub review is COMMENT.
