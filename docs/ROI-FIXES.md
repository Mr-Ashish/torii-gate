# High-ROI minimal fixes (triage)

Evidence from live e2e (Odoo monorepo + hub memory):

| Symptom | Observed |
|---------|----------|
| Monorepo checkout | ~3.5 min for full Odoo PR head (`fetch-depth: 0`) |
| Hermes cold install | ~1–2 min every job |
| Actions cache | `cache write denied` despite `actions: write` |
| Hub memory | Written after run, **not loaded into** next review |
| UX | Only 👀 reaction; no done/fail signal |

## Ranked list

| Rank | ID | Fix | Effort | ROI | Status |
|------|-----|-----|--------|-----|--------|
| 1 | **F1** | PR head `fetch-depth: 1` + **sparse-checkout of changed paths only** | S | 🔥 Huge time on monorepos | **Shipped** (e2e: sparse cone 1 path on Odoo) |
| 2 | **F2** | **Cache Hermes install** (`~/.local` + `~/.hermes` bin) | S | 🔥 Cuts cold install | **Shipped** (cache step; warm on 2nd run) |
| 3 | **F3** | **Preload hub `MEMORY.md`** into `HERMES_HOME` before review | S | 🔥 Real memory-backed reviews | **Shipped** (e2e: `HUB_MEMORY=preloaded` 1126B) |
| 4 | **F4** | Drop broken hermes-home Actions cache (hub is SoT) / soft-fail | XS | Removes noise, simpler | **Shipped** |
| 5 | **F5** | ✅ / ❌ reactions on trigger comment | XS | Clear UX | **Shipped** (`+1`/`-1`) |
| 6 | **F6** | Cap hub clone depth=1 (already ~20) → 1 | XS | Small | **Shipped** |
| 7 | **F11** | Author association allowlist (default OWNER/MEMBER/COLLABORATOR/CONTRIBUTOR; override via `vars.TORII_ALLOWED_ASSOCIATIONS`) | XS | 🔥 Cost control | **Shipped** |
| 8 | **F12** | Replace previous Torii comment (delete prior `<!-- torii-review pr=N` before post) | XS | 🔥 Less PR noise | **Shipped** |
| 9 | **F13** | Fix sparse path `grep -c \|\| echo 0` → empty PR path count was `0\\n0`, forcing full monorepo clone | XS | 🔥 Correct sparse path | **Shipped** |
| 10 | **F14** | Hermes cache: stable key `v3`, save **only on miss** (drop per-run_id thrash) | XS | 🔥 Cache hits + GH cache quota | **Shipped** |
| 11 | **F15** | Config error `pipeline_rc=1` (was 0 → false ✅ reaction) | XS | Honest UX | **Shipped** |
| 12 | **F16** | Association deny → 😕 reaction (no OpenRouter spend) | XS | Visible deny | **Shipped** |
| 13 | **F17** | Drop dead `RUNNER_TEMP` Hermes tree copy after cold install | XS | Faster cold path | **Shipped** |
| 14 | **F18** | Redact secrets in **posted** review (`normalize-review.py` choke-point) | XS | 🔥 Trust — no keys on PR comments | **Shipped** |
| 15 | **F7** | Pin Hermes install (`scripts/hermes-pin.sh` + `TORII_HERMES_COMMIT` + cache key `v4-<pin>`) | S | 🔥 Repro CI | **Shipped** |
| 16 | **F19** | Per-PR re-trigger cooldown (`scripts/cooldown-check.sh`, default 900s) | S | 🔥 Cost/abuse | **Shipped** |
| 17 | **F20** | `scripts/install-torii.sh` copy pack to target repo | S | 🔥 Adoption | **Shipped** |
| 18 | **F8** | Prebaked Hermes runner image + startup benchmark | M | 🔥 Fast CI startup | **Shipped** (docker/ + build workflow + benchmark script) |
| 19 | **F21** | Surface OpenRouter cost/tokens on PR comment + job summary | XS | 🔥 Cost visibility | **Shipped** (`usage-summary.py`) |
| 20 | **F10** | Reusable `workflow_call` + thin hub caller | M | 🔥 Multi-repo DX | **Shipped** (`torii-review-reusable.yml`, `--caller`) |
| 21 | **F22** | Verdict-aware done signal (reaction + commit status + job summary) | XS | 🔥 Trust UX — REQUEST CHANGES no longer looks like ✅ | **Shipped** (`parse-verdict.py`, `report-verdict.sh`) |
| 22 | **F23** | Formal GitHub PR Review event from verdict (Reviews panel) | XS | 🔥 Trust UX — APPROVE/REQUEST_CHANGES/COMMENT as real PR reviews | **Shipped** (`review_event` + `report-verdict.sh`) |
| 23 | **F24** | Dismiss prior Torii PR reviews on re-run (Reviews hygiene) | XS | 🔥 Trust UX — re-@torii no longer stacks APPROVE/REQUEST_CHANGES | **Shipped** (`dismiss-prior-pr-reviews.sh`) |
| 24 | **F25** | Hermes pin single source of truth (no workflow hardcoded SHA) | XS | 🔥 Ops/repro — bump pin in one place | **Shipped** (workflows call `hermes-pin.sh default`) |
| 25 | **F26** | Align default model docs + code (`anthropic/claude-opus-5` SoT) | XS | 🔥 Trust/cost — ops docs no longer understate spend | **Shipped** (`DEFAULT_TORII_MODEL`) |
| 26 | **F27** | Auto banner when PR diff was size-truncated | XS | 🔥 Trust — incomplete context always visible on PR | **Shipped** (`normalize-review --diff-truncated`) |
| 27 | **F28** | Repo-local `.torii/` memory (primary); hub publish opt-in only | S | 🔥 Product memory lives on the target; no hub required | **Shipped** (`publish-run-local.sh`, ingest layout=local, preload local-first) |
| 28 | **F29** | Soft max cost budget (`TORII_MAX_COST_USD`) after F21 usage | XS | 🔥 Cost ops — overage alert on comment + job summary | **Shipped** (`usage-summary.py budget`) |
| 29 | **F30** | Memory health visibility + README F28 truth (no silent local publish fail) | XS | 🔥 Ops — learning loss no longer invisible | **Shipped** (`memory-health.sh`, job summary) |
| 30 | **F31** | Auto-emit `run-bundle.json` every review for Run Console | XS | 🔥 UI ops — real GHA/Modal runs openable without manual pack | **Shipped** (`pack-run-for-ui.py` in orchestrator) |
| 31 | **F32** | Unified trigger (CLI + Modal bit4 webhook + Run Console Run tab) | S | 🔥 Ops — start reviews without hunting docs; webhook spawns only | **Shipped** (`trigger-review.sh`, `enqueue_review`) |
| 32 | **F33** | Webhook auth (GitHub HMAC + bearer token) on Modal doorbell | XS | 🔥 Trust — stop open spend URL | **Shipped** (`webhook_auth.py`, `review_webhook`) |
| 33 | **F9** | Inline GitHub review comments (path-anchored, first changed line) | S | 🔥 Product — findings in Files changed | **Shipped** (`post-inline-comments.py`, report-verdict) |
| 34 | **F34** | Webhook fail-closed by default (opt-in open for dev) | XS | 🔥 Trust — no open spend URL by default | **Shipped** (`TORII_WEBHOOK_ALLOW_OPEN`) |
| 35 | **F9b** | Precise line anchors (`path:LINE` + nearest changed line) | S | 🔥 Product — inline comments land on the right line | **Shipped** (`post-inline-comments.py`, prompt) |
| 36 | **F35** | PR comment ops deep-link (Actions run + run-bundle tip) | XS | 🔥 Ops — open the run without hunting logs | **Shipped** (`ops_footer.py`) |
| 37 | **F36** | Hermes review wall-clock timeout (kill hung agent loops) | XS | 🔥 Cost — stop runaway OpenRouter until job/Modal cap | **Shipped** (`run-with-timeout.py`, default 1500s) |
| 38 | **F37** | Verdict → PR labels (`torii:approve` etc.) | XS | 🔥 Ops — boards/search/automation without parsing comments | **Shipped** (`apply-verdict-labels.py`) |
| 39 | **F38** | Path-glob free skip (docs-only / filtered PRs) | XS | 🔥 Cost — no OpenRouter when every path matches skip globs | **Shipped** (`path-skip-check.py`, opt-in) |
| 40 | **F9c** | Multi-line GitHub apply-suggestion blocks from Code suggestions | S | 🔥 Product — one-click apply on Files changed | **Shipped** (`post-inline-comments.py` suggestions) |
| 41 | **F39** | Modal host parity (F38 path-skip + F22–F37/F9 report-verdict) | S | 🔥 Cost/trust — Modal no longer second-class kitchen | **Shipped** (`modal_parity.py`, `review_pr`) |
| 42 | **F40** | Ops signals in run-bundle + Run Console overview | XS | 🔥 UI ops — timeout/path-skip/budget/truncation visible in 30s | **Shipped** (`pack-run-for-ui` signals, console) |

### Sprint 1 (shipped)

**F1–F6** wall-clock + memory quality.

### Sprint 2 (shipped)

**F11–F12** cost control + comment hygiene.

### Sprint 3 (shipped)

**F13–F17** correctness + cache + reaction honesty.

### Sprint 4 (shipped)

**F18** secret redaction on normalize → PR comment path (aligned with trace/hub scrub patterns).

### Sprint 5 (shipped)

**F7** pin Hermes via `TORII_HERMES_COMMIT` (default known-good SHA in `scripts/hermes-pin.sh` + workflow env); install uses `install.sh --skip-setup --commit … --force-commit`; Actions cache key `torii-hermes-bin-*-v4-<pin>`; set var to `latest`/`main` to float. Trace includes `hermes-pin.txt`.

### Sprint 6 (shipped)

**F19** per-PR re-trigger cooldown: after a *successful* Torii PR comment, further `@torii review` within `TORII_COOLDOWN_SECONDS` (default **900**) skips Hermes/OpenRouter (rocket reaction + job summary). Failures do not start the window. Bypass: `@torii review force`, `workflow_dispatch`, or set cooldown to `0`/`off`.

### Sprint 7 (shipped)

**F8** prebaked Hermes runner: `docker/torii-runner/Dockerfile` + `scripts/build-torii-runner-image.sh` + GHCR publish workflow; optional `vars.TORII_RUNNER_IMAGE` as job `container`; `ensure_hermes` short-circuits on `TORII_HERMES_PREBAKED=1` or `~/.hermes-pin`; startup benchmark under `docs/benchmarks/`.

### Sprint 8 (shipped)

**F20** one-command install: `scripts/install-torii.sh /path/to/target-repo` copies `agent/`, runtime `scripts/`, and `torii-pr-review.yml`; optional `--with-hub-ingest` / `--with-runner-build`; stamp `.torii-install-stamp`.

### Sprint 9 (shipped)

**F21** cost/usage visibility: `scripts/usage-summary.py` appends a `*Cost / usage: …*` line to the posted review from `hermes-usage.json` and writes a job-summary section (model, estimated USD, tokens, API calls, stage timings). Soft no-op when usage is missing.

### Sprint 10 (shipped)

**F10** reusable packaging: `torii-review-reusable.yml` holds the full review job (`workflow_call` + `torii_repository` / `torii_ref` inputs). Thin `torii-pr-review.yml` triggers and calls it. `install-torii.sh --caller` installs only `pack/torii-pr-review-caller.yml` pointing at hub `@main` (no agent/scripts copy — free upgrades). Default pack mode still copies agent/scripts + both workflow files for self-contained targets.

### Sprint 11 (shipped)

**F22** verdict-aware done signal: parse `**Verdict:**` from the posted review → trigger-comment reaction (`+1` / `-1` / `eyes`) and PR-head commit status `torii/review` (`success` / `failure` / `error`). Pipeline failures stay `error`+`-1`. Job summary gets a **Torii verdict (F22)** section. Opt-out: `vars.TORII_COMMIT_STATUS=0`. Required-status checks can require context `torii/review`.

### Sprint 12 (shipped)

**F23** formal PR Review: same verdict map emits `review_event` (`APPROVE` / `REQUEST_CHANGES` / `COMMENT`) and `report-verdict.sh` posts a short GitHub Pull Request Review so the Reviews panel matches the reaction/status. Full Markdown stays on the issue comment (F12). Pipeline failures use `COMMENT` (not REQUEST_CHANGES). APPROVE soft-falls back to COMMENT when GitHub rejects self/bot approve. Opt-out: `vars.TORII_PR_REVIEW=0`.

### Sprint 13 (shipped)

**F24** dismiss prior Torii PR reviews: before posting a new F23 review, `dismiss-prior-pr-reviews.sh` finds bodies with `<!-- torii-pr-review pr=N` and dismisses `APPROVED` / `CHANGES_REQUESTED` (GitHub cannot dismiss `COMMENTED`). Shares `TORII_REPLACE_PREVIOUS` with F12 (0 = leave history). Soft-fail; fixture-testable via `TORII_PR_REVIEWS_FIXTURE`.

### Sprint 14 (shipped)

**F25** Hermes pin single source of truth: remove hardcoded `DEFAULT_HERMES_COMMIT` from workflow `env:` fallbacks. Empty/unset `vars.TORII_HERMES_COMMIT` → after pack checkout, write pin from `scripts/hermes-pin.sh default` into `$GITHUB_ENV`. Explicit `latest`/`main`/`floating` still float. Same for `build-torii-runner.yml`. Bump pin only in `hermes-pin.sh` (Dockerfile ARG may lag for standalone builds).

### Sprint 15 (shipped)

**F26** default model alignment: `DEFAULT_TORII_MODEL=anthropic/claude-opus-5` in `run-hermes-review.sh` is SoT; OPERATIONS/USAGE/.env.example no longer claim `gpt-5-mini` as the script default. Workflow leaves empty `vars.TORII_MODEL` unset so the script default applies (no second hardcoded fallback). Effective model → `.torii-out/torii-model.txt`.

### Sprint 16 (shipped)

**F27** diff-truncation trust banner: when `assemble-context` sets `DIFF_TRUNCATED=true` (PR diff > `MAX_DIFF_BYTES`), `normalize-review.py --diff-truncated` injects a ⚠️ callout before `**Verdict:**` so the posted comment always shows incomplete context even if the model forgets. Job summary gets a **Torii diff truncation (F27)** section.

### Sprint 17 (shipped)

**F28** repo-local `.torii/` memory: target repo is SoT for `MEMORY.md` + slim `runs/{trace}/`. Default `TORII_MEMORY_MODE=local` (hub off). Preload local-first via contents API; hub only if `both|hub` or `TORII_HUB_PUBLISH=1`. Install seeds `.torii/MEMORY.md`. Scripts: `publish-run-local.sh`, `hub-ingest-run.py` layout=local, updated `preload-hub-memory.sh` / `publish-run-to-hub.sh`.

### Sprint 18 (shipped)

**F29** soft max cost budget: repo var `TORII_MAX_COST_USD` (e.g. `1.00`). When `hermes-usage.json` estimated cost exceeds the max, the PR cost footer notes ⚠️ OVER BUDGET, the job summary gains a **Torii cost budget (F29)** section, and Actions emits `::warning::`. Soft only — never fails the review (spend already incurred). Disabled when unset/`0`/`off`. CLI: `usage-summary.py budget|footer|append|step-summary --max-usd …`.

### Sprint 19 (shipped)

**F30** memory health + architecture honesty: `scripts/memory-health.sh` records `MEMORY_SOURCE` / `LOCAL_PUBLISH` / `HUB_PUBLISH` into `.torii-out/memory-health.env`; failed local push emits `::warning::` + job-summary **Memory health** table (does not fail the review). README/public diagrams aligned to F28 local-first (hub opt-in). Install `--caller` tip: pin `uses:` SHA.

### Sprint 20 (shipped)

**F31** auto Run Console bundle: after each review the orchestrator soft-runs `scripts/pack-run-for-ui.py` → `.torii-out/run-bundle.json` (+ copy under the trace dir). Host label auto-detects `gha` / `modal` / `local` (`TORII_HOST` override). Included in existing `torii-out` + trace artifacts; job summary **Torii Run Console bundle (F31)**. Modal `review_pr` sets `TORII_HOST=modal` and returns `run_bundle`. Soft-fail only — never fails the review. Load via `ui/review-console` **Load bundle**.

### Sprint 21 (shipped)

**F32** unified trigger + Modal bit 4 enqueue: `scripts/trigger-review.sh` (`print|local|modal`) is the single entry for starting a review; Modal adds pure `parse_enqueue_payload` / `plan_enqueue` / `enqueue_review` (spawn-only, Hermes never in HTTP path) + `review_webhook` POST endpoint; CLI `modal run … --bit 4` dry-plans (parser self-check) or `--spawn` to enqueue. Run Console **Run** tab + empty-state trigger panel copy local/modal/bit4 commands + sample webhook JSON. Install pack includes `trigger-review.sh`.

### Sprint 22 (shipped)

**F33** webhook auth: pure `scripts/webhook_auth.py` (GitHub `X-Hub-Signature-256` HMAC-SHA256 + `Authorization: Bearer` / `X-Torii-Token`). `review_webhook` reads raw body + headers, authorizes before parse/spawn. Env: `TORII_WEBHOOK_SECRET`, `TORII_WEBHOOK_TOKEN` (fold into Modal `torii-github` secret or app env). Neither set → `auth=open` + warning (dev only). CLI: `webhook_auth.py sign|authorize`. Bit 4 dry plan self-checks auth. Tests: `tests/test_webhook_auth.py`.

### Sprint 23 (shipped)

**F9** path-anchored inline comments: `scripts/post-inline-comments.py` maps Key findings + Blocking bullets onto the **first added line** per file in `pr.diff`, submits a COMMENT PR review with inline notes (`<!-- torii-inline -->`). Default severities `critical,high,blocking`, max 6; opt-out `vars.TORII_INLINE_COMMENTS=0`. Soft-fail; `report-verdict.sh` runs after F23; job summary **Torii inline comments (F9)**. Fixture tests via `TORII_INLINE_FIXTURE`. Precise line numbers / multi-line threads = F9b later.

### Sprint 24 (shipped)

**F34** webhook fail-closed: when neither `TORII_WEBHOOK_SECRET` nor `TORII_WEBHOOK_TOKEN` is set, `authorize_webhook` **denies** by default (F33 left open+warn). Dev escape: `TORII_WEBHOOK_ALLOW_OPEN=1` or `authorize(..., allow_open=True)` / CLI `--allow-open`. Bit 4 dry plan checks `auth_fail_closed_ok`. Production Modal deploys must set secret and/or token.

### Sprint 25 (shipped)

**F9b** precise inline anchors: parse `` `path:LINE` `` / `#L` / `line N` / optional Line column from findings; pin to that line when it is a changed `+` line in `pr.diff`, else **nearest** changed line, else first (F9). Review prompt + SOUL ask for `path:LINE` only when seen in the diff. Plan JSON includes `line_hint` + `anchor` (`exact|nearest|first`).

### Sprint 26 (shipped)

**F35** ops deep-link footer: before posting the PR comment, `ops_footer.py` appends `*Ops (F35): [workflow run](…) · artifact run-bundle.json → ui/review-console*` (optional `TORII_CONSOLE_URL`). Job summary **Torii ops links (F35)**. Opt-out `TORII_OPS_FOOTER=0`. Soft-fail; OpenUI phase 4b partial (no stream/hosted console required).

### Sprint 27 (shipped)

**F36** review wall-clock timeout: `scripts/run-with-timeout.py` wraps `hermes -z` / chat fallback as a process group; default **1500s** (aligned with Modal hard cap). On timeout (exit 124): clear partial output, skip chat fallback (no double spend), honest failure stub + job-summary **Torii Gate review timeout (F36)**. Override `vars.TORII_REVIEW_TIMEOUT_SECONDS` (`0`/`off` disables). Complements F29 (soft $ budget annotates after a finished run; F36 stops a hung loop).

### Sprint 28 (shipped)

**F37** verdict PR labels: after F22/F23 signals, `apply-verdict-labels.py` ensures and applies one managed label — `torii:approve` / `torii:request-changes` / `torii:comment` / `torii:error` — and removes the other three. Pipeline failures always get `error` (never green-wash). Soft-fail; opt-out `vars.TORII_PR_LABELS=0`; prefix override `vars.TORII_LABEL_PREFIX`. Job summary **Torii PR labels (F37)**. Completes trust/ops signal stack for boards and search.

### Sprint 29 (shipped)

**F38** path-glob free skip: when `vars.TORII_SKIP_PATH_GLOBS` is set (`docs` preset or comma globs) and **every** changed path matches, skip Hermes/OpenRouter (no monorepo checkout). Default **off** (empty var). Force: `@torii review force` / `workflow_dispatch`. Stub COMMENT + rocket + F37 labels; job summary **Torii path skip (F38)**. Helper: `scripts/path-skip-check.py`.

### Sprint 30 (shipped)

**F9c** GitHub apply-suggestion blocks: parse `### Code suggestions` (`#### title (`path`)` + ```diff```), map the suggestion’s `-` lines onto contiguous PR `+` lines, post multi-line inline comments with a ```suggestion``` fence (one-click apply in Files changed). Cap `vars.TORII_SUGGESTION_MAX` (default 3); opt-out `vars.TORII_INLINE_SUGGESTIONS=0`. Shares F9 soft-fail + fixture path.

### Sprint 31 (shipped)

**F39** Modal host parity: `review_pr` runs F38 path-skip **before** sparse clone (env `TORII_SKIP_PATH_GLOBS`); on skip posts stub COMMENT + report-verdict labels (no OpenRouter). After a paid run, calls `report-verdict.sh` for commit status / PR review / inline / labels. Sets `TORII_REVIEW_TIMEOUT_SECONDS` (F36). Helper `scripts/modal_parity.py`. App version `0.6.0-f39`.

### Sprint 32 (shipped)

**F40** ops signals in Run Console: `pack-run-for-ui.py` emits `signals` (timeout F36, path-skip F38, over-budget F29, diff-truncated F27 + `flags[]`). Path-skip steps write `ops-signals.env`. Console header chips + Overview **Ops signals (F40)** panel so operators answer “why free-skip / kill / overspend / incomplete?” without grepping artifacts.

### Sprint 33 (shipped)

**F41** Hermes max_turns iteration budget: default **40** tool-calling turns (`agent/config.yaml` + `scripts/max_turns.py` + `HERMES_MAX_ITERATIONS` / config rewrite in `run-hermes-review.sh`). Hermes product default is 500 — unsafe for CI OpenRouter spend. Override `vars.TORII_MAX_TURNS` (`0`/`off` disables). Detects “Iteration budget exhausted” → `hermes-max-turns.env` + job summary. Pack/UI: `signals.max_turns_hit` + `loop` metrics. Complements F36 wall-clock and F29 soft $.

**F47** Hermes `-z` reliability (H14): stop passing non-existent CLI `--max-turns` (argparse treated `N` as subcommand → rc=2 → chat fallback with tool_turns=0). Cap via env+config only; on CLI argv rejection skip chat fallback (`hermes-cli-argv.env`).

### readme-kit (shipped)

YAML config (preferred) + JSON parity; `yaml` npm dep; dead hand-rolled parser removed.
