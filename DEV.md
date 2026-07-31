# DEV — engineering knowledge

> How this repository is built.

## Architecture

- Torii is a gated GitHub Actions control plane, not a chat bot: `@torii review this pr` → gate + per-PR concurrency → dual checkout → restore Hermes memory → assemble context → `hermes -z` → normalize → PR comment → distill memory → cache/artifacts.
- Orchestration is deterministic shell (`scripts/run-torii-review.sh` composes stages and records timings); only the inner review step is LLM-driven, so every run leaves reproducible artifacts.
- Stage → script map: assemble-context.sh (gh pr meta + diff + prompt, no LLM), run-hermes-review.sh (Hermes one-shot over `WORKSPACE_ROOT`; F7 pin via hermes-pin.sh), normalize-review.py (contract/fences/size/HTML marker + secret redact + F27 diff-truncation banner), usage-summary.py (F21 cost footer/job summary + F29 soft max budget), parse-verdict.py + report-verdict.sh (F22 reaction/status + F23 formal PR review + F24 dismiss-prior + F9 inline), post-inline-comments.py (F9 path anchors), distill-memory.sh, post-review-comment.sh, save-trace.sh, publish-run-local.sh (F28 `.torii/`), publish-run-to-hub.sh (opt-in), hub-ingest-run.py (hub + local layouts), pack-run-for-ui.py (F31 Run Console `run-bundle.json`, soft).
- **F20/F10 install:** `scripts/install-torii.sh` is the adoption entrypoint. Default **pack** mode copies `agent/`, runtime scripts, thin `torii-pr-review.yml`, and `torii-review-reusable.yml`. **`--caller`** installs only the hub-managed thin workflow from `pack/torii-pr-review-caller.yml` (no agent/scripts). Optional `--with-hub-ingest` / `--with-runner-build` (pack mode). Stamp `.torii-install-stamp` records `mode=pack|caller` + source SHA.
- Dual workspace separates trust domains: `torii/` holds SOUL + prompts + scripts (from pack default branch or hub checkout), `workspace/` holds only the PR head, `.torii-hermes-home/` holds Hermes config + growing memory.
- **F10 packaging split:** the whole review job lives in `.github/workflows/torii-review-reusable.yml` (`on: workflow_call`, inputs `torii_repository` / `torii_ref`); `torii-pr-review.yml` is a thin trigger-only caller that owns `issue_comment` / `workflow_dispatch`, concurrency and permissions, then `uses:` the reusable job.

## Design decisions

- **F61 suggested test plan:** `scripts/testplan_generation.py` builds prioritized (P0/P1/P2) concrete scenarios from `pr.json` + optional unified diff (symbol extract for Go/Py/JS/Rust). Assemble writes `testplan.md` and injects into the prompt; post-normalize soft-injects `### Suggested test plan` when the model omits/empties it. Toggle `TORII_TESTPLAN` / F55 keys `testplan`, `testplan_max_cases`. Pure code — judgment only refines.
- **F62 FP resolve + memory:** `scripts/fp_resolve_memory.py` mines author replies on Torii inline threads (and path-citing PR comments) for false-positive / resolved language, merges MEMORY.md `## FP patterns`, injects a trusted prompt table at assemble, and updates Hermes MEMORY after distill. Toggle `TORII_FP_RESOLVE` / `fp_resolve`, `fp_resolve_max`. Deterministic — judgment only re-raises with new evidence.
- **F63 domain packs + auto-select:** packs `milvus` / `go` / `cpp` (plus path_globs on odoo/docs). `lens_recipes.select_pack_for_paths` scores globs; default `TORII_LENS_PACK=auto` picks domain pack from PR files at assemble. Explicit pack ids still win. Judgment stays model-side.
- **F64 durable fp-rules self-learn:** structured `.torii/fp-rules.json` (schema v1) written on F62 update, preloaded with MEMORY, carried in hub-payload + local ingest merge. Thin local self-learn loop; multi-tenant federation still deferred.

- **F59 incremental review:** opt-in `TORII_INCREMENTAL=1`. `scripts/incremental_review.py` reads prior Torii comment markers for `head=SHA`, then rewrites `pr.diff` to `base...head` compare patch. Markers gain `head=` via normalize `--head-sha`. Default off (full PR diff).

- **F58 PR description filler:** `scripts/pr_description_filler.py` builds a deterministic description (type, file walkthrough, test-plan checklist, linked #issues) from `pr.json` — no LLM. Modes: `fill-empty` (default, never clobber rich author prose), `markers` (refresh `<!-- torii-description -->` block), `force`. Assemble writes `pr-description.md`; `gh pr edit` only when `TORII_PR_DESCRIPTION_APPLY=1`.

- **F57 Mermaid architecture:** `scripts/mermaid_architecture.py` builds a flowchart from PR changed paths (grouped by package; adjacency edges only — not invented runtime deps). Assemble injects into prompt; post-normalize soft-injects if the model omitted `### Architecture diagram`. Toggle `TORII_MERMAID` / F55 keys `mermaid`, `mermaid_max_nodes`.

- **F56 lens recipes / named packs:** `agent/packs/*.json` declare multi-lens recipes (default, security, docs, odoo, performance, **+ F63 milvus/go/cpp**). `scripts/lens_recipes.py` loads + rewrites the Multi-lens pass/checklist in the assembled prompt. Active pack via `TORII_LENS_PACK` (F55 key `lens_pack`, default **auto** since F63); opt-out `TORII_LENS_PACKS=0`. Judgment remains model-side; pack selection and checklist shape are code.

- **F55 feature toggles:** `scripts/feature_toggles.py` is the single registry for product/quality/ops gates (`fixit_prompts`, `issue_context`, inline, labels, …). Precedence **env > `.torii/toggles.json` (or `TORII_TOGGLES_FILE`) > default**. CLI `list|get|enabled|dump|product|shell` is the agent/operator tool surface; judgment stays out of the registry. New product flags add a `ToggleSpec` + tests, then wire consumers via `is_enabled()` / `get_value()`.

- **F35 ops footer:** `ops_footer.py` appends a deep-link line on the posted PR comment (Actions run URL from `GITHUB_*` env + run-bundle Load tip; optional `TORII_CONSOLE_URL`). Wired in `post-review-comment.sh` before `gh pr comment`. Soft, opt-out `TORII_OPS_FOOTER=0`. Completes OpenUI 4b without requiring a hosted console.
- **F9/F9b inline comments:** `post-inline-comments.py` parses findings/blocking from review Markdown. **F9b** prefers `` `path:LINE` `` (or free-text line hints) when LINE is a changed `+` line in `pr.diff`; else nearest changed line; else first added line. Prompt/SOUL request `path:LINE` only for lines the model actually saw. Never invent lines for GitHub (invalid line → 422). Cap with `TORII_INLINE_MAX` / severity; re-runs can stack COMMENT reviews.
- **F33/F34 webhook auth:** `scripts/webhook_auth.py` is pure stdlib (HMAC-SHA256 GitHub signature + bearer/`X-Torii-Token`). `review_webhook` authorizes **before** parse/spawn. **F34 fail-closed:** neither `TORII_WEBHOOK_SECRET` nor `TORII_WEBHOOK_TOKEN` → denied unless `TORII_WEBHOOK_ALLOW_OPEN=1` (dev escape). Do not put secrets in the repo; fold into Modal secrets.
- **F32 trigger:** `scripts/trigger-review.sh` is the operator entry (`print|local|modal`). Modal bit 4 is spawn-only: `parse_enqueue_payload` + `enqueue_review` / `review_webhook` never run Hermes in the HTTP path; `modal run --bit 4` dry-plans by default (`--spawn` to enqueue). Run Console **Run** tab copies commands — browser is not a kitchen.
- **F31 run-bundle:** after memory-health the orchestrator soft-packs TRACE_DIR (or OUT_DIR) via `pack-run-for-ui.py --soft` into `.torii-out/run-bundle.json` and optionally `TRACE_DIR/run-bundle.json`. Host auto-detect (`TORII_HOST` / `GITHUB_ACTIONS` / Modal). Failures never flip `TORII_STATUS`. Operators download the Actions artifact and **Load bundle** in `ui/review-console` — no manual pack for live runs.
- **F8 prebaked runner:** `ensure_hermes` short-circuits when `TORII_HERMES_PREBAKED=1` or `/root/.hermes-pin`/`$HOME/.hermes-pin` exists and `hermes` is on PATH (image from `docker/torii-runner/`). Workflow optional `container: vars.TORII_RUNNER_IMAGE`; Hermes Actions cache is skipped when prebaked is detected.
- Re-runs replace prior Torii comments by deleting bodies matching the `<!-- torii-review pr=N` marker before posting; set `TORII_REPLACE_PREVIOUS=0` to stack instead.
- Failure UX is always-publish: missing OpenRouter secret, Hermes/model failure, and job crash before the review file each still produce a PR comment (failure stub / low-confidence COMMENT verdict) rather than a silent red X.

- The review step is agentic, not a single completion: Hermes runs with `TORII_TOOLSETS` (default `terminal`) so the reviewer can inspect files under `WORKSPACE_ROOT` beyond the assembled diff, and `capture-hermes-loop.py` records the tool loop.
- Observability is forced on at the env level (`HERMES_TUI_TOOL_PROGRESS=verbose`, `PYTHONUNBUFFERED=1`) so agent/tool activity is recoverable from logs even for a run that later fails.
- `HERMES_HOME` is seeded per run but `MEMORY.md` is explicitly preserved through seeding — the home directory is disposable, the memory file is not.

- The installer copies **itself** into the target pack (`install-torii.sh` is in `RUNTIME_SCRIPTS`), so an installed repo can re-run the install/update from its own tree; executable bits are preserved per-file (`[[ -x "$from" ]] && chmod +x`).
- Installing the pack into the Torii source tree itself (`SRC == DEST`) is refused unless `--force`, explicitly to avoid half-copies over the canonical tree.

- Telemetry is explicitly non-load-bearing: missing, empty, non-dict, or unparseable usage files are soft no-ops that exit 0, and `run-hermes-review.sh` calls the `append` step guarded by `[[ -f … ]]` with `|| notice "usage-summary append soft-failed"` — cost reporting can never fail a review.
- **F29 soft budget** (`TORII_MAX_COST_USD` / `--max-usd`) is opt-in and post-hoc: when estimated cost exceeds the max, footer/job-summary note ⚠️ OVER BUDGET and emit `::warning::`, but the pipeline still exits 0 (OpenRouter spend already happened; this is alerting, not a hard gate).
- Both the PR-comment footer and the job summary are fed from the same usage file so cost is visible without downloading an artifact; number formatting is deliberately lossy/human (tokens as `1.5k`/`10k`/`1.0M`, `n/a` when a field is absent or non-numeric, booleans rejected as numbers).

- The reusable workflow declares **no `permissions:` block** — "Permissions come from the caller workflow/job", so every caller must grant `contents`/`pull-requests`/`issues`/`actions` write itself; a caller that forgets one fails at post/cache time, not at call time.
- Both reusable secrets (`OPENROUTER_API_KEY`, `TORII_HUB_TOKEN`) are declared `required: false` and callers are expected to use `secrets: inherit`; this keeps forks/unfunded repos from failing the `workflow_call` contract up front, with `TORII_HUB_TOKEN` falling back to `GITHUB_TOKEN`.
- `install-torii.sh` preflights **both** F10 files (`.github/workflows/torii-review-reusable.yml` and `pack/torii-pr-review-caller.yml`) before copying anything, so a source tree missing the reusable pair dies before producing a half-install.

- When a budget *is* enabled the cost footer changes shape in both directions: under budget appends ` · budget max $X`, over budget appends ` · ⚠️ OVER BUDGET (max $X)`. The presence of the `budget max` suffix is the cheapest way to confirm from a posted PR comment that the var was actually parsed.
- `budget_status` compares strictly (`cost > max`), and returns `cost: None` when the usage file is missing/empty — so `over_budget` is `False` whenever cost telemetry is absent, keeping the missing-usage case a soft no-op consistent with the other modes.
- Cost rendering is threshold-based, not fixed precision: `>= $0.01` → 2 decimals, `> 0` but smaller → 4 decimals, `0`/unknown → `$0`; cheap-model runs therefore show `$0.0034`-style values on the same line format.

- `scripts/webhook_auth.py` is **pure stdlib** (`hmac`/`hashlib`/`json` only) exposing `authorize_webhook()` + `github_hmac_hex()` plus a `sign|authorize` CLI, so the Modal image needs no extra dependency and the auth decision is unit-testable outside Modal (`tests/test_webhook_auth.py`).

- **F36 review timeout:** `scripts/run-with-timeout.py` wraps `hermes -z` (and the chat fallback) as a child **process group** and kills it after a wall-clock limit, so a hung agent/OpenRouter loop cannot burn the full job cap (GHA 90m / Modal ~25m). Default `TORII_REVIEW_TIMEOUT_SECONDS=1500`; `0`/`off`/`false`/`no` disables.
- The helper never rewrites the child's exit code except timeout→124 (`125` is reserved for invalid usage / empty command), so normal Hermes failures still surface unchanged upstream.
- F36 and F29 are complementary, not overlapping: F29's soft `TORII_MAX_COST_USD` annotates a run that already *finished*, while F36 is the only mechanism that stops a run that never finishes.
- Timeout evidence lands in the trace as `hermes-timeout.env` and `hermes-timeout-seconds.txt`, so a 124 can be distinguished from a model/contract failure after the fact.
- **F42 auto model tier:** opt-in `TORII_MODEL_TIER=auto` picks cheap (`TORII_MODEL_CHEAP`, default `openai/gpt-4.1-mini`) for docs-only or tiny PRs (`≤ TORII_TIER_MAX_FILES` and `≤ TORII_TIER_MAX_BYTES`), else full (`TORII_MODEL_FULL` / `TORII_MODEL` / opus-5). Truncated diffs always get full. Default mode **off** preserves F26 single-model behaviour. Pure helper `scripts/model_tier.py`; `run-hermes-review.sh` re-resolves after `meta.env`; pack signals `model_tier*` + chips `model-cheap`/`model-full`.

- Exactly **one** managed label is applied per run and the other three managed labels from a prior run are removed, so a PR never carries two contradictory Torii verdicts: `APPROVE→{prefix}:approve`, `REQUEST_CHANGES→{prefix}:request-changes`, `COMMENT→{prefix}:comment`, `UNKNOWN`/pipeline failure→`{prefix}:error`.
- Pipeline failure always wins over the parsed verdict (`--pipeline-ok false` ⇒ `error`) — the label channel is deliberately not allowed to green-wash a broken run.
- Labels are created on demand with hardcoded hex colors in `COLORS` (e.g. approve `0E8A16`), so adoption needs no manual label setup on the target repo; the label namespace is `{prefix}:` with prefix from `TORII_LABEL_PREFIX` (default `torii`).

- **F38 path-glob free skip** sits early in the pipeline — after the sparse path list, *before* dual checkout — so a docs-only PR never pays for the monorepo checkout or the Hermes/OpenRouter call.
- It is a whole-PR gate, not a filter: the skip fires only when **every** changed path matches the skip globs; one code file re-enables the paid run.
- Default is **off** (`vars.TORII_SKIP_PATH_GLOBS` empty). Operators opt in with the built-in `docs` preset or a comma glob list (e.g. `*.md,docs/**`); `off` is also accepted as a preset name.
- Two escape hatches keep the gate overridable per run: comment `@torii review force` and `workflow_dispatch` (env form `TORII_SKIP_PATHS_FORCE=1`).
- The helper emits `key=value` stdout (`allowed`, `reason`, `matched_n`, `total_n`, `globs`, `sample`) rather than JSON, matching the other shell-composed stages.

- Anchoring is derived, not trusted: the suggestion's `-` lines must match a **contiguous run of `+` lines in the PR diff for the same file**; a match yields `start_line`/`line` on side RIGHT (multi-line comment), and no match means the suggestion is dropped rather than anchored to a guessed line.
- Two independent kill switches by design: `TORII_INLINE_COMMENTS=0` disables *all* inline output (findings + suggestions), while `TORII_INLINE_SUGGESTIONS=0` disables only F9c and leaves F9/F9b finding notes running.

- Because each flag has a **file source plus a review-text fallback**, a signal survives even when the env file is missing; conversely the F38 path-skip step had to start writing `ops-signals.env` so the skip is durable in the pack rather than only inferrable from the stub comment text.

- `0` / `off` is a supported value meaning "no cap" — treat unset and disabled as different states when reading a run's config.
- Knob surfaces are per-host: GitHub Actions uses `vars.TORII_MAX_TURNS`, Modal uses env `TORII_MAX_TURNS`; `scripts/max_turns.py` is included in the install pack so adopted repos get the same resolver.
- Design was lifted from Hermes' own conversation loop (`agent.max_turns` / `--max-turns` / `HERMES_MAX_ITERATIONS` in NousResearch/hermes-agent); the running list of such borrowings lives in `docs/experiments/hermes-inspired-roi.md`.

- Contract validity is no longer "all REQUIRED_SNIPPETS present": `_looks_like_template_only()` rejects output whose only verdict is the angle-bracket placeholder (`Verdict: < APPROVE | … >`), so a prompt echo fails the contract instead of passing it. Repair reason is stamped as `prompt/template echo or placeholder verdict (F44)`.
- Candidate selection is scored, not positional: `_candidate_score()` slices on `Torii Review — PR #n` headings and penalises placeholder verdicts (-50), `Required Markdown template` / `Trust boundary` text (-30) and a leading `Query:` (-40) while rewarding a concrete verdict (+40); ties go to the *last* candidate since the model answer trails the echo.
- Bare `───` horizontal rules are deliberately **not** treated as TUI chrome (models use them between findings); only explicit chrome lines (`Query:`, `Initializing agent`, `Session:`, `Duration:`, `Messages:`, `╭…╮`/`╰…╯` boxes, `⚕ Hermes`, `⚠ tirith`) are dropped, and the session footer truncates the slice.
- Contract-repair fallback truncates the preserved raw body to 4000 chars (`_(raw truncated by normalizer)_`) so a rejected prompt echo can never be re-posted in full to GitHub.

- **F44 normalize (chat-chrome):** `scripts/normalize-review.py` no longer assumes the review step ran through `hermes -z`; it extracts the real review out of `hermes chat -q` TUI chrome, because the review path can degrade to the chat fallback and would otherwise publish raw wrapper output.
- F44 **promotes unbolded `Verdict:` / `Summary` headings** to the bold contract form so downstream `parse-verdict.py` and the contract checks keep matching when the model drops the bold markers.

- Attempt 1 is preserved rather than overwritten: `review-*.attempt1.raw.md`, `agent-loop-attempt1/`, and `tool-turns-reprompt.env` are emitted so a run bundle shows both passes and why the second happened.

## Pitfalls

- `GITHUB_TOKEN` cannot call `repository_dispatch` (HTTP 403), so the hub publish default is `mode=direct` (clone hub → ingest → push `main`); the dispatch path needs a classic PAT on the target repo.
- Cross-repo publishing requires `TORII_HUB_TOKEN` (PAT with contents write on the hub); only when Torii runs on the hub repo itself is `GITHUB_TOKEN` + `contents: write` sufficient.
- PR title, body, comments, and diff are untrusted input — the agent must not honour embedded instructions, and secrets must never be echoed; `normalize-review.py` redacts `sk-or-…`, `OPENROUTER_API_KEY=…`, and common GitHub tokens before any PR comment is posted (F18); traces/hub scrub again before packaging.
- `MEMORY.md` rotates when it exceeds `MAX_MEMORY_BYTES` (default 100000); unbounded growth would otherwise blow the prompt budget.
- Historical bug classes worth watching (per the ranked ROI backlog): broken Hermes home cache key, sparse-checkout path count bug, and dishonest success reactions on failed runs.

- F26 aligned the default model: `DEFAULT_TORII_MODEL=anthropic/claude-opus-5` in `scripts/run-hermes-review.sh` is the SoT (paid). OPERATIONS/USAGE/README/.env.example must match. Cheaper runs set `vars.TORII_MODEL=openai/gpt-5-mini` (or other OpenRouter id). Effective model is written to `.torii-out/torii-model.txt` each run.
- Pin verification degrades to a substring check: when the install tree has no `.git`, `ensure_hermes` accepts the binary if `hermes --version` merely contains the pin's first 8 chars. A cached install without git metadata can therefore pass the pin gate on weak evidence — check `hermes-pin.txt` in the trace when a run's behaviour looks off for the pinned SHA.
- F25 fixed pin duplication: workflows must **not** embed `|| '<sha>'` fallbacks. Bump only `DEFAULT_HERMES_COMMIT` in `scripts/hermes-pin.sh`. Caveat: `docker/torii-runner/Dockerfile` still has an `ARG HERMES_COMMIT=` default for standalone `docker build` without the helper — image builds via `build-torii-runner.yml` pass the resolved pin and stay in sync.
- GHA empty-string trap: job env `TORII_HERMES_COMMIT: ${{ vars.X }}` with unset var sets the env to `""`, and `hermes-pin.sh resolve` treats empty as **floating**. That is why F25 rewrites empty → `default` into `$GITHUB_ENV` before cache/install — do not remove that step.

- `gh api --paginate` can emit **several concatenated JSON arrays** (one per page), so a plain `json.loads` on its output fails; `cooldown-check.sh` walks the buffer with `json.JSONDecoder().raw_decode` and extends a single list. Reuse that loop for any new paginated `gh api --jq` consumer instead of assuming one array.
- A non-integer `TORII_COOLDOWN_SECONDS` is treated as **disabled** (`reason=disabled_invalid`, warning only) rather than an error — a typo in the repo variable silently removes the spend guard.
- Clock skew is clamped, not trusted: a comment timestamp newer than `now` yields `age=0`, which means a bad clock maximises the cooldown rather than bypassing it.

- Re-running `install-torii.sh` without `--force` is a silent no-op per file: `copy_file` logs `exists (skip, use --force)` and returns 0, so an *upgrade* over an already-installed repo leaves the old pack in place while the command still exits successfully. Upgrades require `--force`.
- A missing source file only warns (`WARN missing in source: $rel/$f`) and continues, so a drifted/incomplete source tree can produce a partially installed pack with exit code 0 — read the stderr log, don't trust the exit status alone.
- `agent/` is copied with `-maxdepth 1 -type f`, so nested files under `agent/` are never installed — keep agent assets flat.
- `usage()` renders help by slicing the file header (`sed -n '2,25p' "$0"`); editing or growing the top comment block silently truncates or corrupts `--help` output.

- `usage-summary.py` is textually coupled to `normalize-review.py`: `_FOOTER_RX` matches the brand footer line to anchor the cost line — edit both together.
- Re-appending is idempotent by design via `_COST_LINE_RX` (`^\*Cost / usage:.*\*$`): an existing cost line is replaced, not stacked. Rewriting that line's shape in one place breaks dedup and produces duplicated footers on re-runs.
- A missing `*Cost / usage: …*` line on a posted review is not necessarily a bug — it is the documented soft no-op when `hermes-usage.json` is absent/empty/malformed. Check the usage file before suspecting the review path.

- The `@torii review` gate `if:` expression is duplicated in *both* the thin caller job and the reusable job. Changing the trigger phrase or association logic in one place silently no-ops (caller filters everything out) or double-gates; keep the two conditions in sync.
- Hub-managed callers point at `…/torii-review-reusable.yml@main`, i.e. unpinned by design — a broken hub `main` breaks every `--caller` target repo at once, and there is no per-target rollback short of editing that `uses:` ref.

- Pipeline failures map to `review_event=COMMENT` on purpose: an OpenRouter outage must not show as "Changes requested" on the product.

- Sparse-checkout path counting is fragile (F13): `grep -c ... || echo 0` emitted `0\n0` for an empty PR path list, which the workflow read as non-zero and fell back to a **full monorepo clone** (observed ~3.5 min on Odoo with `fetch-depth: 0`). Any change to `scripts/sparse-pr-paths.sh` must keep the count a single integer.
- The Hermes Actions cache must be saved **only on miss** with a stable key (F14); an earlier key including `run_id` thrashed the cache (never a hit, burned GH cache quota). Symptom to watch for: `cache write denied` even with `actions: write`.
- Config errors must exit non-zero (F15): a missing-secret path returned `pipeline_rc=0`, so the trigger comment got a false ✅ reaction while no review happened. Reaction/status honesty depends on the pipeline exit code, not on whether a comment was posted.

- The dismiss step is deliberately soft-fail and keyed off the `<!-- torii-pr-review pr=N` marker: a review body whose marker was stripped or reformatted is invisible to F24 and survives re-runs untouched.

- Suggestion volume is capped separately from findings: `TORII_SUGGESTION_MAX` (default 3) bounds apply blocks, `TORII_INLINE_MAX` (default 6) bounds finding notes — raising one does not raise the other, and a review with many `### Code suggestions` will silently post only the first N.
- A well-formed suggestion can still vanish: because mapping requires the `-` lines to line up with contiguous PR `+` lines, a suggestion that rewrites *unchanged* context (or reflows lines) has no valid anchor and is skipped. Confirm with plan mode before assuming the poster failed.
- `TORII_INLINE_SEVERITY` filtering applies to findings only — it is not a lever on F9c, so severity tuning will not suppress apply blocks.

- Budget-exhaustion detection is **log-string matching**, not an exit code: `run-hermes-review.sh` / `scripts/max_turns.py` look for `Iteration budget exhausted`, `max_iterations_reached`, and `Reached maximum iterations`. A Hermes upgrade that rewords any of these silently degrades `signals.max_turns_hit` to false while the run still gets truncated — re-check the three patterns whenever the Hermes pin moves.
- `run-bundle.loop` (not the raw Hermes log) is the intended operator surface for loop behaviour: read `tool_call_turns`, `message_count`, `step_count`, `max_turns` from the bundle rather than re-parsing stdout.

- `hermes -z` is not reliable: an observed `-z` rc=2 on odoo PR #2 forced the `hermes chat -q` path, which is exactly the polluted-output case F44 scrubs. Anything that assumes one-shot mode always wins will regress (tracked as H14).
- `tool_turns=0` on a multi-file PR is a quality smell for an *agentic* review product, not a cheap win: the no-tool mini run on PR #2 returned APPROVE while an earlier GHA tool-using review caught the real gap (missing `format:false` tests). **F45/H12** fail-closes: `scripts/tool_turns_gate.py` downgrades APPROVE→COMMENT, caps score at 55, injects an F45 banner, writes `tool-turns-gate.env` (chip `tool-turns-gate`). Docs-only / single-file exempt; `TORII_TOOL_TURNS_GATE=off` disables.
- **F49/H15 soft re-prompt:** same eligibility as F45, **once** before fail-closed — re-run `hermes -z` with a tool-nudge suffix (`reprompt-write`). Default on (`TORII_TOOL_TURNS_REPROMPT=1`). Evidence: `tool-turns-reprompt.env` + chips `tool-reprompt` / `tool-reprompt-ok`. If tools still 0, F45 still annotates. Doubles cheap-path spend when it fires — intentional recovery cost.
- **F46/H13 SOUL load:** Hermes blocks context files matching threat patterns. Never quote classic injection phrases in `agent/SOUL.md`. Preflight: `scripts/soul_context_scan.py check`; runtime: `soul-context.env` + chip `soul-blocked`.

- The normalizer is a **trust boundary**, not a formatter: never accept a body as a valid review contract just because expected snippets/headings appear in it — prompt echo contains all of them. Contract checks must assert the placeholder-free form.
- `hermes -z` can fail at runtime and fall back to `hermes chat -q` (observed on a cheap run over Mr-Ashish/odoo PR #2); pre-F44 that path would have posted the **entire prompt** as the PR review comment.

- A malformed `hermes -z` argv is silently expensive: argparse exits rc=2, the runner falls back to `hermes chat -q`, and the review completes with **tool_turns=0** (no repo exploration) while still spending. F44 local PR #2 showed exactly this — `hermes-2.stderr` carried `invalid choice: '25'` while `hermes-max-turns.env` reported `max_turns=25`, so the cap looked applied.
- F47 makes CLI argv rejection a distinct, non-fallback failure class: on `invalid choice` / `unrecognized arguments`, skip the chat fallback and write `hermes-cli-argv.env` instead of burning a zero-tool path.

- `HERMES_HOME` is shared across runs, so scanning the whole `agent.log` yields **false `soul_blocked=1`** from stale history — this was observed on a live H16 run whose SOUL preflight was actually clean, and is what F48 fixes. If `soul_blocked` fires, first confirm the evidence came from the current invocation's log slice before treating it as a real SOUL/threat-scanner block.

- Zero-tool reviews were observed *after* F47/F48 landed (odoo e2e corpus #2 and #4 both had mini `tool_turns=0`), so prompt/scoping fixes upstream of the loop do not by themselves make the agent use tools — treat `tool_turns=0` as a recurring residual condition to gate on, not a solved one.

## Patterns

- **F27 truncation banner** is mechanical (not model-dependent): `assemble-context` sets `DIFF_TRUNCATED` in `meta.env` → `run-hermes-review.sh` passes `--diff-truncated` → `inject_diff_truncated_banner()` inserts a blockquote before `**Verdict:**`. Idempotent if the model already wrote a similar note. Raising `MAX_DIFF_BYTES` is the operator control; the banner is honesty, not a skip.
- Secret scrubbing is a single choke-point helper (`redact_secrets()` in `scripts/normalize-review.py`) driven by one `_SECRET_PATTERNS` table: `sk-or-v1-…`, `OPENROUTER_API_KEY=…`, generic `api_key`-style assignments, `gh[pousr]_…`, and `github_pat_…`.
- It is applied **twice per run**: once after `strip_outer_fence` (so the `### Raw agent output` contract-failure fallback is scrubbed too) and again after `ensure_contract` (so repair/templating cannot reintroduce a leak). Adding new output paths in `normalize-review.py` means re-checking both call sites.
- Redaction patterns are intentionally duplicated-but-aligned across `normalize-review.py`, `scripts/save-trace.sh`, and `scripts/build-hub-payload.py`; when a pattern is added to one, add it to all three or posted comments, traces, and hub payloads drift apart in scrub policy.
- Redaction is enforced mechanically at the post step, not delegated to the model: `agent/SOUL.md`'s "never echo secrets" rule remains the intent, but the guarantee lives in the normalize stage.
- Regression tests in `tests/test_normalize_review.py` assert the leaked literal is absent *and* the placeholder (`[OPENROUTER_KEY_REDACTED]` / `[GITHUB_TOKEN_REDACTED]`) is present, including in the broken-output fallback case — copy that both-sided assertion shape for any new pattern.

- `scripts/hermes-pin.sh` is a pure, network-free resolver with a 5-verb CLI (`resolve`, `install-args`, `matches <head>`, `cache-suffix`, `default`); every consumer (workflow step, `run-hermes-review.sh`) calls it instead of re-deriving pin logic, so the pin lives in exactly one place.
- Pin comparison is prefix-tolerant in both directions (`head == pin*` or `pin == head*`), so short and full SHAs interoperate; no pin means `matches` always succeeds (floating mode is a no-op gate).
- `cache-suffix` truncates the pin to 12 chars (or prints `latest` when floating) purely to keep the Actions cache key readable — cache keys are derived, never hand-written.
- `ensure_hermes` in `run-hermes-review.sh` verifies an already-present binary before trusting it: probe `~/.hermes/hermes-agent`, `$HERMES_INSTALL_DIR`, `~/.local/share/hermes-agent` for a `.git` HEAD; on mismatch it reinstalls rather than silently reviewing with the wrong build.
- After any install the script re-exports PATH, sources `~/.bashrc`, runs `hash -r`, then probes `~/.local/bin/hermes`, `~/.hermes/bin/hermes`, `~/.hermes/hermes` — installer layout is treated as unstable, so the binary is located by search, not assumption.

- Gate helpers follow a stdout-contract pattern: `scripts/cooldown-check.sh` prints `allowed=`, `reason=`, `age_s=`, `remaining_s=` key=value lines that the workflow parses straight into `$GITHUB_OUTPUT`, and signals decisions through exit codes — `0` allow, `2` cooldown active (skip paid run), `1` hard error.
- Exit `1` is deliberately **fail-open**: the workflow logs `::warning::F19 cooldown check failed (rc=$RC); fail-open allow` and sets `allowed=true`, so a GitHub API hiccup never blocks reviews (the trade-off is it can also leak a paid run).
- The script is designed for hermetic tests: `TORII_COOLDOWN_FIXTURE` supplies a JSON array of `{created_at, body}` comments (no network) and `NOW_EPOCH` pins the clock — see `tests/test_cooldown_check.py`.

- `scripts/apply-verdict-labels.py` follows the repo's plan/apply split: `plan` computes the label decision with no network, `apply` performs it. `TORII_LABELS_FIXTURE=path.json` makes `apply` **write the planned GitHub API operations to a file instead of invoking `gh`** — that seam is what lets `tests/test_apply_verdict_labels.py` cover the mutation path with no token and no live PR. Prefer this env-fixture pattern over mocking `subprocess` when adding new gh-calling scripts.

- Prompt/contract changes are motivated by rubric evidence, not intuition: the 6-PR `torii-eval` corpus on `Mr-Ashish/odoo` is scored out of 50, and a low per-dimension score (here tool depth on eval #6: 34/50 with that dimension at 2) is what justifies a new feature flag such as F51. Each fix is then validated by a live mini re-score of the same PR under the new build.

- Each fix was validated by a live mini re-score of the same PR under the new build, illustrating an eval-driven tuning loop.
