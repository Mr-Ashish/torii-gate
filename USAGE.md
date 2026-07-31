# USAGE — operational knowledge

> How to work with this repository.

## Run console

- **F31 auto-pack:** every review writes `.torii-out/run-bundle.json` (and `traces/<id>/run-bundle.json`) — download the `torii-out` or `torii-trace` Actions artifact and load it in the console. Soft-fail only.
- **F40–F49 signals:** bundle includes `signals` (timeout / path-skip / over-budget / diff-truncated / max-turns / model-tier / preflight / **tool-turns-gate** / **tool-turns-reprompt** + `flags[]`) and `loop` metrics. Overview shows **Ops signals** + **Agent loop (F41)**; header chips when any flag is set. Path-skip → `ops-signals.env`; F41 → `hermes-max-turns.env`; F42 → `model-tier.env`; F45 → `tool-turns-gate.env`; F49 → `tool-turns-reprompt.env`.
- Manual pack (showcase / older runs): `python3 scripts/pack-run-for-ui.py --dir path/to/run-or-showcase -o run-bundle.json` (`--host gha|modal|local`, `--memory-health path`, `--also path`, `--soft`).
- UI: `cd ui/review-console && npm install && npm run pack-fixture && npm run dev` → http://localhost:5177 → **Load bundle** for any `run-bundle.json`.
- Tabs: Overview, **Run** (F32 trigger), PR, Result, Findings, Diff, Trace, Agent loop, Cost, Memory, Artifacts, Raw review
- Optional OpenUI Lang: `python3 scripts/review-to-openui.py --review review.md -o out.openui`
- Design: Impeccable (`/tmp/impeccable`) · `ui/review-console/PRODUCT.md` + `DESIGN.md`

## Trigger a review (F32)

```bash
./scripts/trigger-review.sh print  owner/repo 123          # commands only
./scripts/trigger-review.sh local  owner/repo 123 --model openai/gpt-4.1-mini
./scripts/trigger-review.sh modal  owner/repo 123 --cheap --no-post
modal run modal_app/app.py --bit 4 --repo owner/repo --pr 123   # dry enqueue plan
```

Run Console **Run** tab copies the same commands + sample webhook JSON. Modal webhook (after `modal deploy`) accepts `{repo,pr,model,post_comment}` or GitHub `@torii review` issue_comment on a PR — spawns only.

### Modal host parity (F39)

Bit 3 `review_pr` now runs F38 path-skip before clone and `report-verdict.sh` after
a paid review (status / PR review / inline / labels). App version `0.6.0-f39`.

```bash
python3 scripts/modal_parity.py path-skip --path README.md --globs docs  # exit 2 = skip
# Set on Modal secret/app env: TORII_SKIP_PATH_GLOBS=docs
modal run modal_app/app.py --bit 3 --repo owner/repo --pr N --model openai/gpt-4.1-mini
```

### Path-glob free skip (F38)

```bash
# Opt-in repo var (empty = disabled):
#   vars.TORII_SKIP_PATH_GLOBS=docs
# or custom: *.md,docs/**,CHANGELOG*

python3 scripts/path-skip-check.py --paths-file pr-paths.txt   # uses env globs
python3 scripts/path-skip-check.py --path README.md --globs docs; echo $?  # 2 = skip
```

When all paths match: rocket reaction, stub COMMENT (no OpenRouter), F37 `torii:comment`.
Force: `@torii review force`.

### Verdict PR labels (F37)

```bash
# Plan only (offline)
python3 scripts/apply-verdict-labels.py plan --verdict REQUEST_CHANGES --pipeline-ok true
# → {"add":"torii:request-changes","remove":["torii:approve",...],...}

# Opt-out: vars.TORII_PR_LABELS=0
# Prefix: vars.TORII_LABEL_PREFIX=torii  → labels torii:approve|request-changes|comment|error
```

Pipeline failures always map to `torii:error` even if the body says APPROVE.
Filter boards with `label:torii:request-changes`.

### Hermes max turns (F41)

Cap Hermes tool-calling iterations so a runaway agent loop cannot burn unbounded
OpenRouter spend (Hermes default is 500 turns — far too high for CI PR review).

| Var | Default | Meaning |
|-----|---------|---------|
| `TORII_MAX_TURNS` | `40` | Cap; `0`/`off` disables (Hermes ~500 default) |

```bash
python3 scripts/max_turns.py resolve          # → 40
TORII_MAX_TURNS=off python3 scripts/max_turns.py resolve   # → off
python3 scripts/max_turns.py detect hermes.stderr          # exit 2 if budget hit
```

On hit: job-summary **Torii max turns (F41)**, `hermes-max-turns.env`, run-bundle
`signals.max_turns_hit` + `loop` metrics. Complements F36 wall-clock timeout.

### Preflight cost gate (F43)

Hard estimate **before** Hermes (complements F29 post-hoc soft budget):

| Var | Default | Meaning |
|-----|---------|---------|
| `TORII_MAX_COST_USD` | unset | Threshold; when set, F43 hard-gates by default |
| `TORII_PREFLIGHT_COST` | `auto` | `auto`/`on`/`hard` / `off` / `estimate` |
| `TORII_PREFLIGHT_ACTION` | `force_cheap` | `force_cheap` → cheap model; `refuse` → stub; `warn` → allow |

```bash
TORII_MAX_COST_USD=0.05 python3 scripts/preflight_cost.py decide \
  --model anthropic/claude-opus-5 --diff-bytes 200000 --file-count 20
# → decision=force_cheap model=openai/gpt-4.1-mini
```

Evidence: `preflight-cost.env`, job-summary **Torii preflight cost (F43)**,
run-bundle chips `preflight-cheap` / `preflight-refuse`.

### SOUL context scan (F46)

Hermes refuses to load `SOUL.md` when it matches prompt-injection patterns.
Torii’s reviewer contract must stay clean:

```bash
python3 scripts/soul_context_scan.py check          # exit 2 if would block
python3 scripts/soul_context_scan.py detect hermes-run.log  # exit 2 if blocked at runtime
```

Evidence: `soul-context.env`, job-summary **Torii SOUL blocked (F46)**, chip `soul-blocked`.

### Tool-turns fail-closed gate (F45)

When Hermes records **0 tool turns** on a **multi-file non-docs** PR, Torii refuses
to leave an **APPROVE** standing (H12 / odoo e2e #2 mini false green):

| Var | Default | Meaning |
|-----|---------|---------|
| `TORII_TOOL_TURNS_GATE` | `1` | `0`/`off` disables |
| `TORII_TOOL_TURNS_MIN_FILES` | `2` | multi-file threshold |
| `TORII_TOOL_TURNS_GATE_VERDICTS` | `APPROVE` | verdicts rewritten to COMMENT |

```bash
python3 scripts/tool_turns_gate.py decide --tool-turns 0 --file-count 4 --path a.js --path b.js
python3 scripts/tool_turns_gate.py apply --review review.md --tool-turns 0 --file-count 4 \
  --path a.js --path b.js --env-out tool-turns-gate.env
```

Action: APPROVE→COMMENT, confidence low, score capped at 55, F45 banner.
Evidence: `tool-turns-gate.env`, job-summary **Torii tool-turns gate (F45)**,
run-bundle chip `tool-turns-gate`.

### Soft tool-turns re-prompt (F49 / H15)

When the **first** Hermes pass records **0 tool turns** on a multi-file non-docs PR,
Torii runs **one** soft re-prompt (`hermes -z` again with a short tool-nudge suffix)
**before** F45 fail-closed. Attempt-1 artifacts are kept under
`review-*.attempt1.raw.md` / `agent-loop-attempt1/`.

| Var | Default | Meaning |
|-----|---------|---------|
| `TORII_TOOL_TURNS_REPROMPT` | `1` | `0`/`off` disables the second pass |
| `TORII_TOOL_TURNS_MIN_FILES` | `2` | shared multi-file threshold with F45 |

```bash
python3 scripts/tool_turns_gate.py reprompt-decide --tool-turns 0 --file-count 4 --path a.js --path b.js
python3 scripts/tool_turns_gate.py reprompt-write \
  --prompt-in prompt.md --prompt-out prompt-reprompt.md \
  --tool-turns 0 --file-count 4 --path a.js --path b.js
```

Evidence: `tool-turns-reprompt.env` (`attempted`, `tool_turns_before/after`, `recovered`),
chips `tool-reprompt` / `tool-reprompt-ok`. F45 still fires if tools remain zero after
the second pass.

### Linked issue context (F53)

During `assemble-context`, Torii extracts issue refs from the PR title/body
(`Fixes #N`, `Closes owner/repo#N`, full issue URLs, bare `#N`) and optionally
from the head branch (`feature/123-foo`), then fetches title/body/comments via
`gh issue view` and injects them into `context.md` + the review prompt as
**claim-to-fix / acceptance criteria**.

| Var | Default | Meaning |
|-----|---------|---------|
| `TORII_ISSUE_CONTEXT` | `1` | `0`/`off` disables |
| `TORII_ISSUE_CONTEXT_MAX` | `3` | max issues to fetch |
| `TORII_ISSUE_CONTEXT_COMMENTS` | `8` | max comments per issue (last N) |
| `TORII_ISSUE_FROM_BRANCH` | `1` | extract issue number from head branch |
| `TORII_ISSUE_CONTEXT_FIXTURE` | unset | JSON array of issues (no network; tests) |

```bash
python3 scripts/linked_issue_context.py extract \
  --repo owner/repo --title "fix crash" --body "Fixes #42"
python3 scripts/linked_issue_context.py assemble \
  --pr-json pr.json --repo owner/repo --out-dir .torii-out
```

Evidence: `linked-issues.md`, `linked-issue-context.env`, run-bundle chip `issue-ctx`.
Soft: fetch failures never block assemble.

### Auto model tier (F42)

Cheap model first for tiny / docs-only PRs when opted in:

| Var | Default | Meaning |
|-----|---------|---------|
| `TORII_MODEL_TIER` | `off` | `auto` picks cheap vs full by size; `cheap`/`full` force |
| `TORII_MODEL_CHEAP` | `openai/gpt-4.1-mini` | Cheap tier |
| `TORII_MODEL_FULL` | opus-5 / `TORII_MODEL` | Full tier |

```bash
TORII_MODEL_TIER=auto python3 scripts/model_tier.py select \
  --path README.md --diff-bytes 400
# model=openai/gpt-4.1-mini tier=cheap reason=docs_only
```

Set repo var `TORII_MODEL_TIER=auto` to enable. Explicit single-model mode remains
the default (`off`). Evidence: `model-tier.env`, job-summary, Run Console chip
`model-cheap` / `model-full`.

### Review timeout (F36)

```bash
# Effective wall-clock seconds (default 1500; env or arg)
python3 scripts/run-with-timeout.py resolve
TORII_REVIEW_TIMEOUT_SECONDS=900 python3 scripts/run-with-timeout.py resolve

# Repo var: vars.TORII_REVIEW_TIMEOUT_SECONDS  (0/off = disabled)
```

On timeout Hermes is process-group killed, chat fallback is skipped, and the
posted review explains the limit. Complements F29 soft $ budget (annotation
only after a finished run).

### Ops footer / deep-link (F35)

```bash
# Preview line (needs GITHUB_REPOSITORY + GITHUB_RUN_ID in env for the Actions link)
GITHUB_REPOSITORY=owner/repo GITHUB_RUN_ID=123 python3 scripts/ops_footer.py line
# Inject into a review before post
python3 scripts/ops_footer.py append --review .torii-out/review-3.md
```

Optional hosted console: `TORII_CONSOLE_URL=https://…`. Opt-out: `TORII_OPS_FOOTER=0`.

### Inline comments (F9 / F9b / F9c)

```bash
# Plan only (no API) — findings + F9c suggestions (kind=suggestion, ```suggestion body)
python3 scripts/post-inline-comments.py plan \
  --review docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/review.md \
  --diff docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/pr.diff

# Post (needs gh auth + head SHA)
python3 scripts/post-inline-comments.py post \
  --review review.md --diff pr.diff --repo owner/name --pr 3 --commit "$HEAD_SHA"
```

Key findings File column may use `` `path:LINE` `` when LINE is a new line from the diff (F9b).
Code suggestions with ```diff``` → multi-line GitHub apply blocks (F9c).
Opt-out: `vars.TORII_INLINE_COMMENTS=0` (all) or `vars.TORII_INLINE_SUGGESTIONS=0` (F9c only).
Caps: `TORII_INLINE_MAX`, `TORII_SUGGESTION_MAX`.

### Webhook auth (F33/F34)

```bash
# Sign a body like GitHub would (fixture / curl)
python3 scripts/webhook_auth.py sign --secret "$TORII_WEBHOOK_SECRET" --body payload.json
# Authorize
python3 scripts/webhook_auth.py authorize --secret "$TORII_WEBHOOK_SECRET" --body payload.json \
  --header "X-Hub-Signature-256: sha256=…"
# Dev open (not for production)
python3 scripts/webhook_auth.py authorize --allow-open --body payload.json
```

Set `TORII_WEBHOOK_SECRET` (GitHub) and/or `TORII_WEBHOOK_TOKEN` (Bearer) on the Modal function env. **F34:** neither → denied (fail-closed). Local smoke only: `TORII_WEBHOOK_ALLOW_OPEN=1`.
## Common commands

- Install Torii into another repo (self-contained pack): `./scripts/install-torii.sh /path/to/target-repo` (`--force` overwrite; `--dry-run` preview).
- Hub-managed thin install (F10, no agent/scripts copy): `./scripts/install-torii.sh --caller /path/to/target-repo`.
- Build prebaked Hermes runner image: `./scripts/build-torii-runner-image.sh` (optional `PUSH=1`).
- Benchmark Hermes startup paths: `SKIP_COLD=1 ./scripts/benchmark-hermes-startup.sh` → `docs/benchmarks/`.

```bash
devmemory extract --fixture sample-auth-module --apply
```

- Inspect the effective Hermes pin locally without network: `scripts/hermes-pin.sh resolve` (empty output = floating), `scripts/hermes-pin.sh default` (baked-in known-good SHA — **F25 single source of truth** for CI when `vars.TORII_HERMES_COMMIT` is unset), `scripts/hermes-pin.sh install-args` (exact `install.sh` args), `scripts/hermes-pin.sh cache-suffix` (Actions cache key suffix).
- Check whether an installed tree satisfies the pin: `scripts/hermes-pin.sh matches <git-head-sha>` — exit 0 means acceptable (short/full SHA prefixes both count).
- Per-run pin actually used is recorded at `.torii-out/hermes-pin.txt` and shipped in the trace artifact — read it before blaming the model for a behaviour change.

- Explicit-flag form of the installer (equivalent to the positional target): `./scripts/install-torii.sh --dest /path/to/target-repo [--source /path/to/torii] [--dry-run|--force]`.
- Hub-only extra: `--with-hub-ingest` additionally copies `.github/workflows/ingest-torii-run.yml` (install this on the hub repo, not on app repos).
- Image-building extra: `--with-runner-build` copies `build-torii-runner.yml`, `docker/torii-runner/{Dockerfile,README.md}`, plus `scripts/build-torii-runner-image.sh` and `scripts/benchmark-hermes-startup.sh`, which are otherwise excluded from target packs.

- F21/F29 cost/usage CLI: `python3 scripts/usage-summary.py footer --usage <hermes-usage.json>` (print line); `… append --usage … --review review.md` (inject into posted body); `… step-summary --usage … --timings timings.json` (Actions job summary Markdown); `… budget --usage … --max-usd 1.00` (F29 kv: `over_budget=`). Soft max also via env `TORII_MAX_COST_USD`. All modes exit 0 with no/minimal output when the usage file is missing or empty.
- F27 truncation banner: `python3 scripts/normalize-review.py -i raw.md -o out.md --pr N --diff-truncated` injects a ⚠️ callout when the assembled PR diff was capped (`MAX_DIFF_BYTES`; set via env / repo var).

- Regenerate the Hermes startup comparison: `./scripts/benchmark-hermes-startup.sh` writes `docs/benchmarks/hermes-startup-latest.md` (cold Hermes install measured at ~1–2 min, which is what the cache/prebaked-image paths are traded against).

- Ops footer toggles (F35): set repo/env var `TORII_OPS_FOOTER=0` to suppress the italic ops line on posted reviews; set `TORII_CONSOLE_URL` to a hosted Run Console base URL to add a hosted console link next to the Actions run link (empty by default, so only the workflow-run link plus the `run-bundle.json` → `ui/review-console` Load-bundle tip are emitted).

- Show the effective review timeout (resolves `TORII_REVIEW_TIMEOUT_SECONDS`, else the 1500s default): `python3 scripts/run-with-timeout.py resolve`.
- Self-check the killer without spending on a model: `python3 scripts/run-with-timeout.py --seconds 2 -- sleep 10` → exits **124**.
- Both `--seconds N -- cmd …` and the positional `N -- cmd …` forms are accepted; regression coverage is `tests/test_run_with_timeout.py`.
- Override per repo with `vars.TORII_REVIEW_TIMEOUT_SECONDS`; set `0` or `off` to disable the timeout entirely.

- Preview the F37 label decision without touching GitHub: `python3 scripts/apply-verdict-labels.py plan --verdict REQUEST_CHANGES --pipeline-ok true`.
- Capture the intended API calls instead of executing them: `TORII_LABELS_FIXTURE=ops.json python3 scripts/apply-verdict-labels.py apply …`.
- Disable / rename per target repo with repo variables `TORII_PR_LABELS=0` and `TORII_LABEL_PREFIX=<prefix>`; the run's outcome is echoed in the job summary section **Torii PR labels (F37)**.

- Enable free skip on a target repo: set repo variable `TORII_SKIP_PATH_GLOBS` to `docs` (preset) or a comma list such as `*.md,docs/**`. Unset/empty = feature off.
- Self-check the gate before wiring it up (exit code is the answer): `python3 scripts/path-skip-check.py --path README.md --path docs/a.md --globs docs` → exit 2 (skip); `python3 scripts/path-skip-check.py --path src/x.py --path README.md --globs docs` → exit 0 (allow).
- Batch form for a real PR path list: `python3 scripts/path-skip-check.py --paths-file pr-paths.txt` (paths come from `scripts/sparse-pr-paths.sh`).

- **F50 severity calibration:** enabled by default; disable per-run with `TORII_SEVERITY_CALIBRATION=0`. Regression coverage lives in `tests/test_severity_calibration.py`.
- **F53 linked issue context:** enabled by default; disable with `TORII_ISSUE_CONTEXT=0`. Tests: `tests/test_linked_issue_context.py`.
- The gate can be re-run **offline against an existing run directory** to re-score a past review without new OpenRouter spend — this is how the odoo e2e corpus was re-scored (#2 36→42/50, #5 37→40/50, #4 no-op) after the gate landed.
- Console/bundle side: a `sev-cal` chip appears in the run bundle `signals` when the gate fired, so an upgraded verdict is visible in the Run Console without reading the review body.

## Setup

- Install on each target repo's **default branch** (workflow only runs from default branch):
  - **Pack:** `./scripts/install-torii.sh /path/to/target-repo` — `agent/`, runtime `scripts/`, thin caller + local reusable.
- Required secret: `OPENROUTER_API_KEY`.
- **Memory (F28):** each target repo owns review memory under **`.torii/`** (committed slim pack: `MEMORY.md` + `runs/{trace}/`). Install seeds `.torii/MEMORY.md`. Fat debug traces stay Actions artifacts only.
- Optional hub memory: set repo var `TORII_MEMORY_MODE=both` or `hub`, and/or `TORII_HUB_PUBLISH=1`, plus secret `TORII_HUB_TOKEN` (PAT with contents write on the hub). Default mode is `local` (hub off).
- Optional repo variables: `TORII_MODEL` (script default `anthropic/claude-opus-5` — F26 SoT in `run-hermes-review.sh`; override e.g. `openai/gpt-5-mini` for cheaper runs), `TORII_HERMES_COMMIT` (pin Hermes SHA; default in `scripts/hermes-pin.sh`; `latest`/`main` = floating tip), `TORII_COOLDOWN_SECONDS` (default 900; `0`/`off` disables re-trigger cooldown), `TORII_RUNNER_IMAGE` (optional prebaked Hermes container image, F8), `TORII_MAX_COST_USD` (F29 soft budget USD; `0`/`off`/unset disables), `TORII_MAX_TURNS` (F41 Hermes iteration cap; default 40; `0`/`off` disables), `TORII_MODEL_TIER` (F42 `off`|`auto`|`cheap`|`full`; default off), `TORII_MODEL_CHEAP` / `TORII_MODEL_FULL`, `TORII_MEMORY_MODE` (`local`|`hub`|`both`), `TORII_MEMORY_PATH` (default `.torii`), `TORII_HUB_REPO`, `TORII_HUB_MODE`, `TORII_HUB_PUBLISH`, `TORII_ALLOWED_ASSOCIATIONS`, `TORII_REPLACE_PREVIOUS`, `MAX_DIFF_BYTES`, `MAX_MEMORY_BYTES`.
- Trigger a review by commenting `@torii review this pr` (or `@torii review`) on the PR.

### Repo-local memory commands

```bash
# Offline: write slim pack under a checkout's .torii/
export CLIENT_PAYLOAD_FILE=path/to/client_payload.json
export TORII_INGEST_LAYOUT=local TORII_MEMORY_ROOT=/path/to/target
python3 scripts/hub-ingest-run.py

# Preload preference dry-run (needs network/API or curl stub): local path first
REPO=owner/name HERMES_HOME=/tmp/hh TORII_MEMORY_MODE=local bash scripts/preload-hub-memory.sh
```

## Debugging

- Local dry-run (needs authenticated `gh`, network, and `.env` with `OPENROUTER_API_KEY`): `./scripts/review-local.sh owner/repo 123`; add `POST_COMMENT=1` to actually comment on the PR.
- Two artifacts per run: `torii-out-pr<N>-run<id>` (full `.torii-out/` + memory snapshot, 14 days) and `torii-trace-pr<N>-run<id>` (structured redacted trace, 90 days).
- Fetch a trace with `gh run download <run-id> -R owner/repo -n torii-trace-pr<N>-run<run-id>`.
- Trace layout under `traces/pr{N}-run{RUN_ID}-a{ATTEMPT}/`: `meta.json`, `trace.json`, `prompt.md`, `context.md`, `pr.json`/`pr.diff`, `review.raw.md` (Hermes stdout) vs `review.md` (posted body), `hermes.stderr`, `timings.json`, `memory-before.md`/`memory-after.md` — diff raw vs normalized to isolate contract violations, and before/after memory to verify distill.
- `scripts/capture-hermes-loop.py` turns a run into a step-by-step agent-loop dump (API calls, tool turns, messages, token/cost estimates) as in `docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/`.

- Reproduce a cooldown decision offline (no `gh`, no network): `TORII_COOLDOWN_FIXTURE=/tmp/comments.json NOW_EPOCH=1753963200 bash scripts/cooldown-check.sh 1` — fixture is a JSON array of `{created_at, body}` objects; read the `allowed=`/`reason=`/`remaining_s=` lines and the exit code (0 allow, 2 skip, 1 error).

- For deeper digging, `hermes-usage.json` travels with the run package (see `docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/hermes-usage.json` for a captured example alongside `timings.json`).
- If cost/token values render as `n/a`, the usage JSON parsed but the specific field was absent or non-numeric; if the whole line is missing, the usage file itself was missing/empty and every subcommand no-opped.

- Exercise the F27 local ingest offline against any checkout: `CLIENT_PAYLOAD_FILE=path/to/client_payload.json TORII_INGEST_LAYOUT=local TORII_MEMORY_ROOT=/path/to/target python3 scripts/hub-ingest-run.py` — prints `MEMORY=`, `RUN_DIR=`, `LAYOUT=local` and writes `.torii-ingest-summary.txt` at the root.
- Check which memory source a run would use: `REPO=owner/name HERMES_HOME=/tmp/hh TORII_MEMORY_MODE=local bash scripts/preload-hub-memory.sh` (needs network or a curl stub); the `MEMORY_SOURCE=` line on stdout tells you local vs hub vs seed.

- Inline comments (F9) can be exercised with zero GitHub API calls: set `TORII_INLINE_FIXTURE=<path>` and `post-inline-comments.py` writes the review payload JSON to that path instead of calling `gh api` — this is the hook the tests use, and the same trick works for inspecting a real run's intended anchors.
- `TORII_INLINE_DIFF` overrides which diff file the anchor resolution reads, so you can replay anchoring against a saved `pr.diff` (e.g. from a showcase trace) without re-assembling context.
- Identify Torii's inline output by its markers when auditing a PR: each comment body carries `<!-- torii-inline -->` and the enclosing review body carries `<!-- torii-inline-review pr=N -->`.

- Disable just apply blocks while keeping inline findings: set repo variable `TORII_INLINE_SUGGESTIONS=0`. Tune volume with `TORII_SUGGESTION_MAX` (default 3).
- Posted suggestion comments carry the `<!-- torii-suggestion -->` marker — grep for it to tell F9c output apart from F9/F9b finding notes when auditing a PR.

- Set the cap per host: repo variable `TORII_MAX_TURNS` for GitHub Actions, env `TORII_MAX_TURNS` for Modal; use `0` or `off` to disable the cap entirely when debugging a long legitimate review.
- F41 regression gate: `pytest` (204 passing at 50c4712), `bash -n scripts/run-hermes-review.sh`, and `cd ui/review-console && npm run pack-fixture && npm run build` — the shell syntax check and fixture re-pack are what catch the config-rewrite and bundle-shape halves.

- Multi-PR e2e corpus for scoring review quality: `Mr-Ashish/odoo` PRs #1–#3 (PRs titled `torii-eval …`); per-run output for the F44 investigation was kept under `.torii-out-e2e-pr2-f44/` with the write-up in `docs/experiments/odoo-e2e-benchmark.md` / `odoo-e2e-learn.md`.

- If a posted review looks like the review prompt itself, the run took the `hermes chat -q` fallback (`hermes -z` failed) and normalization was bypassed/stale. Re-run `python3 scripts/normalize-review.py` over `review.raw.md`: a placeholder verdict line (`**Verdict:** < APPROVE | … >`) means prompt echo and must be rejected, not published.

- When triaging a `soul_blocked` signal, export `HERMES_LOG_OFFSET` (byte offset of `HERMES_HOME/logs/agent.log` taken *before* launching Hermes) so `scripts/capture-hermes-loop.py` packages only this run's slice; a block reported without an offset is likely stale history.
- To separate CLI failures from model behaviour on a cheap-model run, read the captured loop metrics: `hermes -z` health shows up as absence of invalid-choice/chat-fallback in the log slice, while `tool_turns=0` in the bundle's `loop` section means the model never entered the agentic loop and the F45 `tool-turns-gate.env` verdict downgrade is expected rather than a bug.

## Troubleshooting

- Confirm which Torii version a target repo runs: read `.torii-install-stamp` (`mode=pack|caller`, `source_sha`) and compare with `git -C <torii-source> rev-parse --short HEAD`. A stale `source_sha` after a re-install means files were skipped — re-run with `--force`. For `mode=caller`, runtime tracks hub `main`, not the stamp alone.
- Installer output is entirely on stderr; capture it with `./scripts/install-torii.sh /path/to/repo 2>&1 | tee install.log` and grep for `exists (skip` / `WARN missing` before committing the pack.
- Preview exactly what would be written (including the stamp) with `--dry-run`; lines are prefixed `DRY  <from> → <to>`.

- No `torii/review` or `torii/gate` status on the PR head: check (1) repo variable `TORII_COMMIT_STATUS` is not `0` (that is the documented opt-out), (2) the caller workflow grants `statuses: write`.
- A neutral 👀 reaction plus `success` means the verdict line was parsed as `UNKNOWN` (or the review was a genuine COMMENT); inspect `review.md` in the trace artifact for a line starting with `**Verdict:**` before blaming the status code path.

- To make Torii gate merges, add **`torii/gate`** as the required status check (security-aware: REQUEST CHANGES or a non-clean Security audit → `failure`). Keep `torii/review` as the F22 signal if you want both; prefer `torii/gate` for branch protection. Pipeline failures still report `error` on `torii/review` with 👎.

- A review that comes back as a COMMENT failure stub with **no findings** is often an F36 timeout, not a bad model run: check the job summary for **Torii Gate review timeout (F36)** and the trace for `hermes-timeout.env` / `hermes-timeout-seconds.txt` before blaming the prompt or contract.
- After a timeout there is intentionally no chat-fallback review body — do not read the missing fallback as a broken fallback path.
- If long PRs legitimately need more wall time, raise `TORII_REVIEW_TIMEOUT_SECONDS` rather than disabling it; on Modal the 1500s default is already aligned with the `review_pr` hard cap, so a larger value will be cut off by the host instead.

- Matching is `fnmatch`-based, so glob depth is literal: the `docs` preset ships both `docs/**` and `**/docs/**` because a top-level-only pattern will not match nested `pkg/docs/…`. Add both shapes when writing custom globs for a monorepo.
- Extension globs in the preset are unanchored (`*.md`, `*.mdx`, `*.rst`, `*.txt`, `*.adoc`) — a `.txt` fixture inside `src/` counts as skippable, so audit `matched_n`/`sample` output before trusting the preset on a mixed repo.

- Reproduce an argv-shape regression in isolation before blaming Hermes: `hermes -z "hello" --max-turns 25` reproduces the argparse error, and the same command without the flag runs clean.
- Post-F47, a run that still lands in `hermes chat -q` fallback is **not** a max-turns argv problem — check for real hermes/install/API failures (missing binary, install step, OpenRouter/API errors) and look for `hermes-cli-argv.env` to tell an argv rejection apart from a runtime failure.
- Triage order for a suspiciously fast/shallow review: confirm `tool_turns` in the run artifacts, then read `hermes-*.stderr` for `invalid choice` / `unrecognized arguments` before trusting `hermes-max-turns.env`, which records the *intended* cap rather than the accepted one.

## F22/F23 verdict signals

After each run Torii derives a **verdict signal** from the posted review body:

| Verdict | Trigger reaction | Commit status `torii/review` | PR review event (F23) |
|---------|------------------|------------------------------|------------------------|
| APPROVE | `+1` | `success` | `APPROVE` (fallback `COMMENT`) |
| REQUEST CHANGES | `-1` | `failure` | `REQUEST_CHANGES` |
| COMMENT | `eyes` | `success` | `COMMENT` |
| Pipeline failed | `-1` | `error` | `COMMENT` (not REQUEST_CHANGES) |

### Product gate (`torii/gate`)

A second status context is posted from `scripts/torii_gate_status.py` (workflow step **Torii Gate status (torii/gate)**):

| Condition | `torii/gate` state |
|-----------|-------------------|
| APPROVE + Security audit clean (`No` / empty / n/a) | `success` (open) |
| REQUEST CHANGES | `failure` (closed) |
| Security audit non-empty concern (any verdict) | `failure` (closed) |
| COMMENT / advisory without security concern | `success` (advisory) |
| Missing review artifact | `error` |

- Prefer **`torii/gate`** as the required branch-protection check for a security merge gate.
- CLI: `python3 scripts/torii_gate_status.py review.md --json --strict`
- Optional hard job fail: repo var `TORII_GATE_STRICT=1`
- Offline smoke (pack): `./scripts/smoke-torii-gate.sh`

- CLI: `python3 scripts/parse-verdict.py review.md --pipeline-rc 0` (kv lines; includes `review_event=`)
- Disable commit status: repo var `TORII_COMMIT_STATUS=0` (turns off both `torii/review` and `torii/gate` posts)
- Disable formal PR review: repo var `TORII_PR_REVIEW=0`
- F22 status context override: `TORII_STATUS_CONTEXT` (default `torii/review`; does not change `torii/gate`)
- Full Markdown stays on the **issue comment** (F12 replace). F23 posts a short Reviews-panel review with marker `<!-- torii-pr-review pr=N`.
