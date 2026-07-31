# Repository context

- **root:** `/Users/ashishmishra/Documents/experiments/pr-review-agent`
- **assembled_at:** 2026-07-31T17:42:12Z

## git status

```
M DEV.md
 M USAGE.md
 M agent/DEV.md
 M docs/showcase/devmemory-dogfood-torii/README.md
 M docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.json
 M docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.md
 M docs/showcase/devmemory-dogfood-torii/agent-loop/agent.log
 M docs/showcase/devmemory-dogfood-torii/agent-loop/usage.json
 M docs/showcase/devmemory-dogfood-torii/apply.json
 M docs/showcase/devmemory-dogfood-torii/extract.raw.md
 M docs/showcase/devmemory-dogfood-torii/hermes-usage.json
 M docs/showcase/devmemory-dogfood-torii/meta.env
 M docs/showcase/devmemory-dogfood-torii/preview.diff
 M docs/showcase/devmemory-dogfood-torii/preview.json
 M docs/showcase/devmemory-dogfood-torii/prompt.md
 M docs/showcase/devmemory-dogfood-torii/repo-context.md
 M docs/showcase/devmemory-dogfood-torii/summary.md
 M docs/showcase/devmemory-dogfood-torii/timings.json
 M docs/showcase/devmemory-dogfood-torii/units.json
?? .torii-out-e2e-pr2-f44/
?? .torii-out-e2e-pr2-f49/
?? .torii-out-e2e-pr2-h16/
?? .torii-out-e2e-pr4-f49/
?? .torii-out-e2e-pr4-h16/
?? .torii-out-e2e-pr5-f49/
?? .torii-out-e2e-pr6-f49/
?? .torii-out-e2e-pr6-f51/
```

## recent log

```
7070077 docs: mark F52 multi-lens worktree merged (PR #2)
b774307 feat(review): F52 multi-lens checklist (H28) (#2)
a5e26f1 docs(experiments): H27 F51 re-score #6 34→39/50
083b223 dogfood: F51 tool-depth knowledge + showcase
d27b477 feat(review): F51 tool-depth nudge after F49 (H26)
```

## tree (sample)

```
DEV.md
README.generated.md
README.md
USAGE.md
demo/__init__.py
demo/hello.py
ui/DEV.md
ui/review-console/DESIGN.md
ui/review-console/DEV.md
ui/review-console/PRODUCT.md
ui/review-console/README.md
ui/review-console/index.html
ui/review-console/package-lock.json
ui/review-console/package.json
ui/review-console/tsconfig.json
ui/review-console/tsconfig.tsbuildinfo
ui/review-console/vite.config.ts
ui/review-console/src/App.tsx
ui/review-console/src/main.tsx
ui/review-console/src/parse.ts
ui/review-console/src/styles.css
ui/review-console/src/types.ts
ui/review-console/src/vite-env.d.ts
readme-kit/DEV.md
readme-kit/README.md
readme-kit/package-lock.json
readme-kit/package.json
readme-kit/bin/readme-kit.mjs
readme-kit/packs/ai-agent/pack.json
readme-kit/examples/torii/README.generated.md
readme-kit/examples/torii/readme.config.json
readme-kit/examples/torii/readme.config.yaml
readme-kit/scripts/generate-hero-options.mjs
readme-kit/themes/flame.json
readme-kit/themes/terminal.json
readme-kit/src/build.mjs
readme-kit/src/cli.mjs
readme-kit/src/load.mjs
readme-kit/src/render/badges.mjs
readme-kit/src/render/document.mjs
readme-kit/src/assets/hero-options.mjs
readme-kit/src/assets/hero-svg.mjs
docker/torii-runner/DEV.md
docker/torii-runner/Dockerfile
docker/torii-runner/README.md
docker/torii-runner/USAGE.md
memory/DEV.md
memory/README.md
memory/index.json
memory/repos/Mr-Ashish--odoo/MEMORY.md
memory/repos/Mr-Ashish--odoo/latest.json
memory/repos/Mr-Ashish--torii-pr-review-agent/MEMORY.md
memory/repos/Mr-Ashish--torii-pr-review-agent/latest.json
modal_app/DEV.md
modal_app/USAGE.md
modal_app/__init__.py
modal_app/app.py
tests/test_apply_verdict_labels.py
tests/test_cooldown_check.py
tests/test_default_model.py
tests/test_dismiss_prior_pr_reviews.py
tests/test_gate_helpers.py
tests/test_hermes_pin.py
tests/test_hub_ingest.py
tests/test_install_torii.py
tests/test_local_memory.py
tests/test_max_turns.py
tests/test_memory_health.py
tests/test_modal_parity.py
tests/test_model_tier.py
tests/test_normalize_review.py
tests/test_ops_footer.py
tests/test_pack_run_for_ui.py
tests/test_parse_verdict.py
tests/test_path_skip_check.py
tests/test_post_inline_comments.py
tests/test_preflight_cost.py
tests/test_review_to_openui.py
tests/test_run_with_timeout.py
tests/test_severity_calibration.py
tests/test_soul_context_scan.py
tests/test_tool_turns_gate.py
tests/test_trigger_review.py
tests/test_usage_summary.py
tests/test_webhook_auth.py
pack/DEV.md
pack/README.md
pack/torii-pr-review-caller.yml
agent/DEV.md
agent/MEMORY.seed.md
agent/SOUL.md
agent/config.yaml
agent/review-prompt.md
docs/ARCHITECTURE.md
docs/MODAL.md
docs/OPENUI-INTEGRATION.md
docs/OPERATIONS.md
docs/README-BRANDING-ECOSYSTEM.md
docs/README-KIT-MVP.md
docs/ROI-FIXES.md
docs/experiments/2026-07-31-f31-run-bundle.md
docs/experiments/2026-07-31-f32-trigger.md
docs/experiments/2026-07-31-f33-webhook-auth.md
docs/experiments/2026-07-31-f34-webhook-fail-closed.md
docs/experiments/2026-07-31-f35-ops-footer.md
docs/experiments/2026-07-31-f36-review-timeout.md
docs/experiments/2026-07-31-f37-verdict-labels.md
docs/experiments/2026-07-31-f38-path-skip.md
docs/experiments/2026-07-31-f39-modal-parity.md
docs/experiments/2026-07-31-f40-ops-signals.md
docs/experiments/2026-07-31-f41-max-turns.md
docs/experiments/2026-07-31-f42-model-tier.md
docs/experiments/2026-07-31-f43-preflight-cost.md
docs/experiments/2026-07-31-f44-normalize-chat-chrome.md
docs/experiments/2026-07-31-f45-tool-turns-gate.md
docs/experiments/2026-07-31-f46-soul-context-scan.md
docs/experiments/2026-07-31-f48-soul-detect-scope.md
docs/experiments/2026-07-31-f49-soft-reprompt.md
docs/experiments/2026-07-31-f50-severity-calibration.md
docs/experiments/2026-07-31-f51-tool-depth.md
docs/experiments/2026-07-31-f52-multi-lens.md
docs/experiments/2026-07-31-f9-inline-comments.md
docs/experiments/2026-07-31-f9b-precise-anchors.md
docs/experiments/2026-07-31-f9c-suggestions.md
docs/experiments/2026-07-31-roi-fire.md
docs/experiments/f28-repo-local-memory.md
docs/experiments/hermes-inspired-roi.md
docs/experiments/loop-idle-streak.txt
docs/experiments/loop-no-work-streak.md
docs/experiments/odoo-e2e-benchmark.md
docs/experiments/odoo-e2e-learn.md
docs/experiments/parallel-worktrees.md
docs/blog/building-torii-agentic-pr-review.md
docs/benchmarks/hermes-startup-latest.json
docs/benchmarks/hermes-startup-latest.md
docs/benchmarks/local-memory-ingest-latest.md
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/README.md
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/context.md
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/e2e-agentic-trace.mmd
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/files.txt
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/hermes-run.log
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/hermes-usage.json
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/hermes.stderr
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/memory-after.md
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/meta.env
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/meta.json
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/pr.diff
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/pr.json
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/prompt.md
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/review.md
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/review.raw.md
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/timings.json
docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/trace.json
docs/showcase/devmemory-dogfood-torii/README.md
docs/showcase/devmemory-dogfood-torii/apply.json
docs/showcase/devmemory-dogfood-torii/extract.raw.md
docs/showcase/devmemory-dogfood-torii/hermes-usage.json
docs/showcase/devmemory-dogfood-torii/meta.env
docs/showcase/devmemory-dogfood-torii/preview.diff
docs/showcase/devmemory-dogfood-torii/preview.json
docs/showcase/devmemory-dogfood-torii/prompt.md
docs/showcase/devmemory-dogfood-torii/repo-context.md
docs/showcase/devmemory-dogfood-torii/session.md
docs/showcase/devmemory-dogfood-torii/summary.md
docs/showcase/devmemory-dogfood-torii/timings.json
docs/showcase/devmemory-dogfood-torii/units.json
docs/showcase/openui-torii/README.md
docs/showcase/openui-torii/review-modal-e2e.openui
docs/showcase/openui-torii/review.openui
scripts/apply-verdict-labels.py
scripts/assemble-context.sh
scripts/association-allowed.sh
scripts/benchmark-hermes-startup.sh
scripts/build-hub-payload.py
scripts/build-torii-runner-image.sh
scripts/capture-hermes-loop.py
scripts/cooldown-check.sh
scripts/dismiss-prior-pr-reviews.sh
scripts/distill-memory.sh
scripts/hermes-pin.sh
scripts/hub-ingest-run.py
scripts/install-torii.sh
scripts/max_turns.py
scripts/memory-health.sh
scripts/modal_parity.py
scripts/model_tier.py
scripts/normalize-review.py
scripts/ops_footer.py
scripts/pack-run-for-ui.py
scripts/parse-verdict.py
scripts/path-skip-check.py
scripts/post-inline-comments.py
scripts/post-review-comment.sh
scripts/preflight_cost.py
scripts/preload-hub-memory.sh
scripts/publish-run-local.sh
scripts/publish-run-to-hub.sh
scripts/report-verdict.sh
scripts/review-local.sh
scripts/review-to-openui.py
```

## git diff

```
diff --git a/DEV.md b/DEV.md
index 5e879fb..d2ac846 100644
--- a/DEV.md
+++ b/DEV.md
@@ -125,7 +125,6 @@
 - `hermes -z` is not reliable: an observed `-z` rc=2 on odoo PR #2 forced the `hermes chat -q` path, which is exactly the polluted-output case F44 scrubs. Anything that assumes one-shot mode always wins will regress (tracked as H14).
 - `tool_turns=0` on a multi-file PR is a quality smell for an *agentic* review product, not a cheap win: the no-tool mini run on PR #2 returned APPROVE while an earlier GHA tool-using review caught the real gap (missing `format:false` tests). **F45/H12** fail-closes: `scripts/tool_turns_gate.py` downgrades APPROVE→COMMENT, caps score at 55, injects an F45 banner, writes `tool-turns-gate.env` (chip `tool-turns-gate`). Docs-only / single-file exempt; `LUFFY_TOOL_TURNS_GATE=off` disables.
 - **F49/H15 soft re-prompt:** same eligibility as F45, **once** before fail-closed — re-run `hermes -z` with a tool-nudge suffix (`reprompt-write`). Default on (`LUFFY_TOOL_TURNS_REPROMPT=1`). Evidence: `tool-turns-reprompt.env` + chips `tool-reprompt` / `tool-reprompt-ok`. If tools still 0, F45 still annotates. Doubles cheap-path spend when it fires — intentional recovery cost.
-- **F50/H20 severity calibration:** when the review **self-reports** a test gap under **APPROVE**, `scripts/severity_calibration.py` upgrades to **REQUEST CHANGES**, caps score at 69 (override `LUFFY_SEVERITY_SCORE_CAP`), injects F50 banner, chip `sev-cal`. Default on (`LUFFY_SEVERITY_CALIBRATION=1`). Complements SOUL/prompt rules that missing tests for claimed production fixes are Blocking. Offline: odoo #2 F49 APPROVE 95→RC (GHA parity); #5 tests:no; #4 clean. Offline re-score without new OpenRouter spend via `severity_calibration.py apply` on an existing review.md.
 - **F46/H13 SOUL load:** Hermes blocks context files matching threat patterns. Never quote classic injection phrases in `agent/SOUL.md`. Preflight: `scripts/soul_context_scan.py check`; runtime: `soul-context.env` + chip `soul-blocked`.
 
 - The normalizer is a **trust boundary**, not a formatter: never accept a body as a valid review contract just because expected snippets/headings appear in it — prompt echo contains all of them. Contract checks must assert the placeholder-free form.
@@ -158,3 +157,5 @@
 - The script is designed for hermetic tests: `LUFFY_COOLDOWN_FIXTURE` supplies a JSON array of `{created_at, body}` comments (no network) and `NOW_EPOCH` pins the clock — see `tests/test_cooldown_check.py`.
 
 - `scripts/apply-verdict-labels.py` follows the repo's plan/apply split: `plan` computes the label decision with no network, `apply` performs it. `LUFFY_LABELS_FIXTURE=path.json` makes `apply` **write the planned GitHub API operations to a file instead of invoking `gh`** — that seam is what lets `tests/test_apply_verdict_labels.py` cover the mutation path with no token and no live PR. Prefer this env-fixture pattern over mocking `subprocess` when adding new gh-calling scripts.
+
+- Prompt/contract changes are motivated by rubric evidence, not intuition: the 6-PR `torii-eval` corpus on `Mr-Ashish/odoo` is scored out of 50, and a low per-dimension score (here tool depth on eval #6: 34/50 with that dimension at 2) is what justifies a new feature flag such as F51. Each fix is then validated by a live mini re-score of the same PR under the new build.
diff --git a/USAGE.md b/USAGE.md
index 10a1fca..2e75fca 100644
--- a/USAGE.md
+++ b/USAGE.md
@@ -329,6 +329,9 @@ REPO=owner/name HERMES_HOME=/tmp/hh LUFFY_MEMORY_MODE=local bash scripts/preload
 - When triaging a `soul_blocked` signal, export `HERMES_LOG_OFFSET` (byte offset of `HERMES_HOME/logs/agent.log` taken *before* launching Hermes) so `scripts/capture-hermes-loop.py` packages only this run's slice; a block reported without an offset is likely stale history.
 - To separate CLI failures from model behaviour on a cheap-model run, read the captured loop metrics: `hermes -z` health shows up as absence of invalid-choice/chat-fallback in the log slice, while `tool_turns=0` in the bundle's `loop` section means the model never entered the agentic loop and the F45 `tool-turns-gate.env` verdict downgrade is expected rather than a bug.
 
+- F51 tool-depth wording is covered by the `tool_depth_h26` case in `tests/test_tool_turns_gate.py` (same suite as F45/F49), so depth guidance is asserted from the gate side rather than in a separate test file.
+- Any edit to `agent/SOUL.md` must also pass the SOUL preflight/context scan (`tests/test_soul_context_scan.py`) — run it alongside the tool-turns suite when changing reviewer scope wording.
+
 ## Troubleshooting
 
 - Confirm which Torii version a target repo runs: read `.torii-install-stamp` (`mode=pack|caller`, `source_sha`) and compare with `git -C <torii-source> rev-parse --short HEAD`. A stale `source_sha` after a re-install means files were skipped — re-run with `--force`. For `mode=caller`, runtime tracks hub `main`, not the stamp alone.
diff --git a/agent/DEV.md b/agent/DEV.md
index 8d1fcb9..66aaa39 100644
--- a/agent/DEV.md
+++ b/agent/DEV.md
@@ -28,6 +28,8 @@
 
 - It shifts the objective from *whether* the reviewer used tools (F45/F49) to *how deeply* it looked, which is why it ships as prompt text plus an assertion in the existing tool-turns suite rather than a new post-review gate script.
 
+- The depth requirement is stated on three surfaces that must stay in sync: `build_reprompt_suffix` (F49 re-prompt text), the **Workspace** section of `agent/review-prompt.md`, and the **Scope** section of `agent/SOUL.md`. Changing the wording in only one place leaves the other two contradicting it.
+
 ## Pitfalls
 
 - Same anchoring applies to `**Score:** <int>[/100]` and `**Confidence:** low|medium|high` — score/confidence are parsed only for reporting, and a missed match yields empty strings rather than an error.
diff --git a/docs/showcase/devmemory-dogfood-torii/README.md b/docs/showcase/devmemory-dogfood-torii/README.md
index ec4ac0b..a18cea8 100644
--- a/docs/showcase/devmemory-dogfood-torii/README.md
+++ b/docs/showcase/devmemory-dogfood-torii/README.md
@@ -1,4 +1,4 @@
-# Showcase · `run-20260731T225816-aeecec`
+# Showcase · `run-20260731T231135-bf6235`
 
 Live dogfood run of **devmemory on itself**.
 
@@ -6,7 +6,7 @@ Live dogfood run of **devmemory on itself**.
 |-------|-------|
 | model | `anthropic/claude-opus-5` |
 | hermes_rc | 0 |
-| units | 2 |
+| units | 3 |
 
 ## Files
 
diff --git a/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.json b/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.json
index da24c4e..32cad2a 100644
--- a/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.json
+++ b/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.json
@@ -1,33 +1,33 @@
 {
-  "run_id": "run-20260731T225816-aeecec",
+  "run_id": "run-20260731T231135-bf6235",
   "model": "anthropic/claude-opus-5",
   "hermes_rc": 0,
-  "units": 2,
-  "summary": "The F51 session's durable content is mostly already merged into agent/DEV.md and USAGE.md by the prior devmemory run; two bullets were dropped in that merge and remain unrecorded: the three-surface sync contract for tool-depth wording, and the shallow-read evidence that 0\u21921 tool recovery is not real inspection.",
+  "units": 3,
+  "summary": "The session shipped F51, a tool-depth nudge layered on the F49 soft re-prompt, and the durable knowledge is where that depth requirement lives (three coupled surfaces: build_reprompt_suffix, agent/review-prompt.md Workspace section, agent/SOUL.md Scope) plus the concrete failure mode it encodes (recovering tool turns but reading large files with head-only). The eval-driven tuning loop (rubric dimension score on the odoo eval corpus motivating a prompt change) is also durable context. USAGE.md test-running guidance was already applied in the working tree, so no usage unit is emitted.",
   "usage": {
-    "estimated_cost_usd": 0.2659555,
+    "estimated_cost_usd": 0.2644225,
     "cost_status": "estimated",
     "cost_source": "provider_models_api",
     "input_tokens": 2,
-    "output_tokens": 1781,
-    "cache_read_tokens": 20016,
-    "cache_write_tokens": 33826,
-    "reasoning_tokens": 298,
-    "total_tokens": 55625,
+    "output_tokens": 1775,
+    "cache_read_tokens": 0,
+    "cache_write_tokens": 35206,
+    "reasoning_tokens": 238,
+    "total_tokens": 36983,
     "api_calls": 1,
     "model": "anthropic/claude-opus-5",
     "provider": "openrouter",
-    "session_id": "20260731_225817_5a835f",
+    "session_id": "20260731_231137_f0e9a5",
     "completed": true,
     "failed": false,
     "service_tier": null
   },
   "timings": {
-    "assemble_s": 0.634,
-    "extract_s": 27.168,
-    "normalize_s": 0.0,
-    "apply_s": 0.344,
-    "total_s": 28.151
+    "assemble_s": 1.169,
+    "extract_s": 27.936,
+    "normalize_s": 0.002,
+    "apply_s": 2.657,
+    "total_s": 31.769
   },
   "messages_meta": {
     "db": "/Users/ashishmishra/Documents/experiments/pr-review-agent/.devmemory/hermes-home/state.db",
diff --git a/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.md b/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.md
index 504dd50..1294524 100644
--- a/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.md
+++ b/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.md
@@ -1,31 +1,31 @@
-# Agent loop · `run-20260731T225816-aeecec`
+# Agent loop · `run-20260731T231135-bf6235`
 
 - **model:** `anthropic/claude-opus-5`
 - **hermes_rc:** 0
-- **units:** 2
-- **at:** 2026-07-31T17:28:44Z
+- **units:** 3
+- **at:** 2026-07-31T17:42:06Z
 
 ## Summary
 
-The F51 session's durable content is mostly already merged into agent/DEV.md and USAGE.md by the prior devmemory run; two bullets were dropped in that merge and remain unrecorded: the three-surface sync contract for tool-depth wording, and the shallow-read evidence that 0→1 tool recovery is not real inspection.
+The session shipped F51, a tool-depth nudge layered on the F49 soft re-prompt, and the durable knowledge is where that depth requirement lives (three coupled surfaces: build_reprompt_suffix, agent/review-prompt.md Workspace section, agent/SOUL.md Scope) plus the concrete failure mode it encodes (recovering tool turns but reading large files with head-only). The eval-driven tuning loop (rubric dimension score on the odoo eval corpus motivating a prompt change) is also durable context. USAGE.md test-running guidance was already applied in the working tree, so no usage unit is emitted.
 
 ## Usage
 
 ```json
 {
-  "estimated_cost_usd": 0.2659555,
+  "estimated_cost_usd": 0.2644225,
   "cost_status": "estimated",
   "cost_source": "provider_models_api",
   "input_tokens": 2,
-  "output_tokens": 1781,
-  "cache_read_tokens": 20016,
-  "cache_write_tokens": 33826,
-  "reasoning_tokens": 298,
-  "total_tokens": 55625,
+  "output_tokens": 1775,
+  "cache_read_tokens": 0,
+  "cache_write_tokens": 35206,
+  "reasoning_tokens": 238,
+  "total_tokens": 36983,
   "api_calls": 1,
   "model": "anthropic/claude-opus-5",
   "provider": "openrouter",
-  "session_id": "20260731_225817_5a835f",
+  "session_id": "20260731_231137_f0e9a5",
   "completed": true,
   "failed": false,
   "service_tier": null
@@ -36,11 +36,11 @@ The F51 session's durable content is mostly already merged into agent/DEV.md and
 
 ```json
 {
-  "assemble_s": 0.634,
-  "extract_s": 27.168,
-  "normalize_s": 0.0,
-  "apply_s": 0.344,
-  "total_s": 28.151
+  "assemble_s": 1.169,
+  "extract_s": 27.936,
+  "normalize_s": 0.002,
+  "apply_s": 2.657,
+  "total_s": 31.769
 }
 ```
 
diff --git a/docs/showcase/devmemory-dogfood-torii/agent-loop/agent.log b/docs/showcase/devmemory-dogfood-torii/agent-loop/agent.log
index 85aaf2f..34c07e1 100644
--- a/docs/showcase/devmemory-dogfood-torii/agent-loop/agent.log
+++ b/docs/showcase/devmemory-dogfood-torii/agent-loop/agent.log
@@ -1,23 +1,23 @@
-2026-07-31 22:58:17,006 INFO hermes_cli.plugins: Plugin 'browser-browser-use' registered browser provider: browser-use
-2026-07-31 22:58:17,006 INFO hermes_cli.plugins: Plugin 'browser-browserbase' registered browser provider: browserbase
-2026-07-31 22:58:17,007 INFO hermes_cli.plugins: Plugin 'browser-firecrawl' registered browser provider: firecrawl
-2026-07-31 22:58:17,069 INFO hermes_cli.plugins: Plugin 'deepinfra' registered image_gen provider: deepinfra
-2026-07-31 22:58:17,069 INFO hermes_cli.plugins: Plugin 'fal' registered image_gen provider: fal
-2026-07-31 22:58:17,070 INFO hermes_cli.plugins: Plugin 'krea' registered image_gen provider: krea
-2026-07-31 22:58:17,070 INFO hermes_cli.plugins: Plugin 'openai' registered image_gen provider: openai
-2026-07-31 22:58:17,070 INFO hermes_cli.plugins: Plugin 'openai-codex' registered image_gen provider: openai-codex
-2026-07-31 22:58:17,071 INFO hermes_cli.plugins: Plugin 'openrouter' registered image_gen provider: openrouter
-2026-07-31 22:58:17,071 INFO hermes_cli.plugins: Plugin 'openrouter' registered image_gen provider: nous
-2026-07-31 22:58:17,071 INFO hermes_cli.plugins: Plugin 'xai' registered image_gen provider: xai
-2026-07-31 22:58:17,076 INFO hermes_cli.plugins: Plugin 'deepinfra' registered video_gen provider: deepinfra
-2026-07-31 22:58:17,076 INFO hermes_cli.plugins: Plugin 'fal' registered video_gen provider: fal
-2026-07-31 22:58:17,076 INFO hermes_cli.plugins: Plugin 'xai' registered video_gen provider: xai
-2026-07-31 22:58:17,077 INFO hermes_cli.plugins: Plugin 'web-brave-free' registered web provider: brave-free
-2026-07-31 22:58:17,078 INFO hermes_cli.plugins: Plugin 'web-ddgs' registered web provider: ddgs
-2026-07-31 22:58:17,078 INFO hermes_cli.plugins: Plugin 'web-exa' registered web provider: exa
-2026-07-31 22:58:17,079 INFO hermes_cli.plugins: Plugin 'web-firecrawl' registered web provider: firecrawl
-2026-07-31 22:58:17,080 INFO hermes_cli.plugins: Plugin 'web-parallel' registered web provider: parallel
-2026-07-31 22:58:17,080 INFO hermes_cli.plugins: Plugin 'web-searxng' registered web provider: searxng
-2026-07-31 22:58:17,080 INFO hermes_cli.plugins: Plugin 'web-tavily' registered web provider: tavily
-2026-07-31 22:58:17,081 INFO hermes_cli.plugins: Plugin 'web-xai' registered web provider: xai
-2026-07-31 22:58:17,094 INFO hermes_cli.plugins: Plugin discovery complete: 54 found, 47 enabled
+2026-07-31 23:11:36,453 INFO hermes_cli.plugins: Plugin 'browser-browser-use' registered browser provider: browser-use
+2026-07-31 23:11:36,454 INFO hermes_cli.plugins: Plugin 'browser-browserbase' registered browser provider: browserbase
+2026-07-31 23:11:36,454 INFO hermes_cli.plugins: Plugin 'browser-firecrawl' registered browser provider: firecrawl
+2026-07-31 23:11:36,522 INFO hermes_cli.plugins: Plugin 'deepinfra' registered image_gen provider: deepinfra
+2026-07-31 23:11:36,522 INFO hermes_cli.plugins: Plugin 'fal' registered image_gen provider: fal
+2026-07-31 23:11:36,522 INFO hermes_cli.plugins: Plugin 'krea' registered image_gen provider: krea
+2026-07-31 23:11:36,523 INFO hermes_cli.plugins: Plugin 'openai' registered image_gen provider: openai
+2026-07-31 23:11:36,523 INFO hermes_cli.plugins: Plugin 'openai-codex' registered image_gen provider: openai-codex
+2026-07-31 23:11:36,524 INFO hermes_cli.plugins: Plugin 'openrouter' registered image_gen provider: openrouter
+2026-07-31 23:11:36,524 INFO hermes_cli.plugins: Plugin 'openrouter' registered image_gen provider: nous
+2026-07-31 23:11:36,524 INFO hermes_cli.plugins: Plugin 'xai' registered image_gen provider: xai
+2026-07-31 23:11:36,529 INFO hermes_cli.plugins: Plugin 'deepinfra' registered video_gen provider: deepinfra
+2026-07-31 23:11:36,529 INFO hermes_cli.plugins: Plugin 'fal' registered video_gen provider: fal
+2026-07-31 23:11:36,530 INFO hermes_cli.plugins: Plugin 'xai' registered video_gen provider: xai
+2026-07-31 23:11:36,531 INFO hermes_cli.plugins: Plugin 'web-brave-free' registered web provider: brave-free
+2026-07-31 23:11:36,531 INFO hermes_cli.plugins: Plugin 'web-ddgs' registered web provider: ddgs
+2026-07-31 23:11:36,532 INFO hermes_cli.plugins: Plugin 'web-exa' registered web provider: exa
+2026-07-31 23:11:36,533 INFO hermes_cli.plugins: Plugin 'web-firecrawl' registered web provider: firecrawl
+2026-07-31 23:11:36,533 INFO hermes_cli.plugins: Plugin 'web-parallel' registered web provider: parallel
+2026-07-31 23:11:36,534 INFO hermes_cli.plugins: Plugin 'web-searxng' registered web provider: searxng
+2026-07-31 23:11:36,534 INFO hermes_cli.plugins: Plugin 'web-tavily' registered web provider: tavily
+2026-07-31 23:11:36,535 INFO hermes_cli.plugins: Plugin 'web-xai' registered web provider: xai
+2026-07-31 23:11:36,548 INFO hermes_cli.plugins: Plugin discovery complete: 54 found, 47 enabled
diff --git a/docs/showcase/devmemory-dogfood-torii/agent-loop/usage.json b/docs/showcase/devmemory-dogfood-torii/agent-loop/usage.json
index 1b26ce5..cd709b7 100644
--- a/docs/showcase/devmemory-dogfood-torii/agent-loop/usage.json
+++ b/docs/showcase/devmemory-dogfood-torii/agent-loop/usage.json
@@ -1,17 +1,17 @@
 {
-  "estimated_cost_usd": 0.2659555,
+  "estimated_cost_usd": 0.2644225,
   "cost_status": "estimated",
   "cost_source": "provider_models_api",
   "input_tokens": 2,
-  "output_tokens": 1781,
-  "cache_read_tokens": 20016,
-  "cache_write_tokens": 33826,
-  "reasoning_tokens": 298,
-  "total_tokens": 55625,
+  "output_tokens": 1775,
+  "cache_read_tokens": 0,
+  "cache_write_tokens": 35206,
+  "reasoning_tokens": 238,
+  "total_tokens": 36983,
   "api_calls": 1,
   "model": "anthropic/claude-opus-5",
   "provider": "openrouter",
-  "session_id": "20260731_225817_5a835f",
+  "session_id": "20260731_231137_f0e9a5",
   "completed": true,
   "failed": false,
   "service_tier": null
diff --git a/docs/showcase/devmemory-dogfood-torii/apply.json b/docs/showcase/devmemory-dogfood-torii/apply.json
index 75b15f5..87b99dc 100644
--- a/docs/showcase/devmemory-dogfood-torii/apply.json
+++ b/docs/showcase/devmemory-dogfood-torii/apply.json
@@ -4,8 +4,17 @@
     "kind": "dev",
     "action": "merge",
     "section": "Design decisions",
-    "bytes": 7115,
+    "bytes": 7417,
     "applied": true,
     "unit_path": "agent"
+  },
+  {
+    "path": "DEV.md",
+    "kind": "dev",
+    "action": "merge",
+    "section": "Patterns",
+    "bytes": 30123,
+    "applied": true,
+    "unit_path": "."
   }
 ]
diff --git a/docs/showcase/devmemory-dogfood-torii/extract.raw.md b/docs/showcase/devmemory-dogfood-torii/extract.raw.md
index 22888a0..2d876b5 100644
--- a/docs/showcase/devmemory-dogfood-torii/extract.raw.md
+++ b/docs/showcase/devmemory-dogfood-torii/extract.raw.md
@@ -1,6 +1,6 @@
 ```json
 {
-  "summary": "The F51 session's durable content is mostly already merged into agent/DEV.md and USAGE.md by the prior devmemory run; two bullets were dropped in that merge and remain unrecorded: the three-surface sync contract for tool-depth wording, and the shallow-read evidence that 0→1 tool recovery is not real inspection.",
+  "summary": "The session shipped F51, a tool-depth nudge layered on the F49 soft re-prompt, and the durable knowledge is where that depth requirement lives (three coupled surfaces: build_reprompt_suffix, agent/review-prompt.md Workspace section, agent/SOUL.md Scope) plus the concrete failure mode it encodes (recovering tool turns but reading large files with head-only). The eval-driven tuning loop (rubric dimension score on the odoo eval corpus motivating a prompt change) is also durable context. USAGE.md test-running guidance was already applied in the working tree, so no usage unit is emitted.",
   "session_ids": ["dogfood-torii-session"],
   "units": [
     {
@@ -8,10 +8,10 @@
       "path": "agent",
       "action": "merge",
       "section": "Design decisions",
-      "content": "- **F51/H26 tool depth** is not a new gate — it is prompt wording that must stay in sync across three surfaces: `build_reprompt_suffix` (the F49 soft re-prompt suffix), the **Workspace** section of `agent/review-prompt.md`, and the **Scope** section of `agent/SOUL.md`. Editing only one leaves a re-prompted attempt with depth guidance the first attempt never saw (or vice versa), so treat the three as a single contract.\n- It shifts the objective from *whether* the reviewer used tools (F45/F49) to *how deeply* it looked, which is why it ships as prompt text plus an assertion in the existing tool-turns suite rather than a new post-review gate script.",
+      "content": "- **F51 tool depth (H26)** layers on top of the F49 soft re-prompt: F49 only fixed *whether* the model used tools, F51 fixes *how deeply*. The re-prompt suffix and the reviewer contract now require reading the actual diff hunks plus `rg` + a line-range read of each changed symbol, and explicitly forbid head-only reads of large files (e.g. `head -80` on a multi-thousand-line module).\n- The depth requirement is stated on three surfaces that must stay in sync: `build_reprompt_suffix` (F49 re-prompt text), the **Workspace** section of `agent/review-prompt.md`, and the **Scope** section of `agent/SOUL.md`. Changing the wording in only one place leaves the other two contradicting it.",
       "evidence": [
-        "Fix: build_reprompt_suffix + review-prompt Workspace + SOUL Scope require diff hunks / rg + line-range on changed symbols; forbid head-only large-file reads",
-        "F51: tool-depth nudge after F49 soft re-prompt (H26)"
+        "F51: tool-depth nudge after F49 soft re-prompt (H26)",
+        "Fix: build_reprompt_suffix + review-prompt Workspace + SOUL Scope require diff hunks / rg + line-range on changed symbols; forbid head-only large-file reads"
       ],
       "confidence": "high"
     },
@@ -20,11 +20,24 @@
       "path": "agent",
       "action": "merge",
       "section": "Pitfalls",
-      "content": "- A non-zero `tool_turns` after the F49 re-prompt is not evidence of real inspection: on odoo eval PR #6 the recovered attempt went 0→**1** tool call and spent it on `head -80` of a large `misc.py`, never reaching the changed `street_split` code around **L1925** — score 34/50 with depth dimension **D8=2**. When judging a re-prompted run, check *which lines* were read, not the `tool-turns-*` counters.",
+      "content": "- A non-zero tool-turn count is not evidence of a real read: the F49 recovery case went 0→1 tool turns yet the single call was `head -80` on a large module and the changed function (~L1925) was never opened. Treat \"tools used\" and \"changed symbol actually read\" as separate signals when triaging a shallow review.",
       "evidence": [
-        "Evidence: odoo eval #6 F49 recovered 0→1 tools but only `head -80` on large misc.py; never read street_split ~L1925; score 34/50 D8=2"
+        "odoo eval #6 F49 recovered 0→1 tools but only `head -80` on large misc.py; never read street_split ~L1925"
       ],
       "confidence": "high"
+    },
+    {
+      "kind": "dev",
+      "path": ".",
+      "action": "merge",
+      "section": "Patterns",
+      "content": "- Prompt/contract changes are motivated by rubric evidence, not intuition: the 6-PR `torii-eval` corpus on `Mr-Ashish/odoo` is scored out of 50, and a low per-dimension score (here tool depth on eval #6: 34/50 with that dimension at 2) is what justifies a new feature flag such as F51. Each fix is then validated by a live mini re-score of the same PR under the new build.",
+      "evidence": [
+        "score 34/50 D8=2",
+        "H27 live mini re-score #6 under F51",
+        "Corpus: 6 torii-eval PRs on Mr-Ashish/odoo all scored"
+      ],
+      "confidence": "medium"
     }
   ]
 }
diff --git a/docs/showcase/devmemory-dogfood-torii/hermes-usage.json b/docs/showcase/devmemory-dogfood-torii/hermes-usage.json
index 1b26ce5..cd709b7 100644
--- a/docs/showcase/devmemory-dogfood-torii/hermes-usage.json
+++ b/docs/showcase/devmemory-dogfood-torii/hermes-usage.json
@@ -1,17 +1,17 @@
 {
-  "estimated_cost_usd": 0.2659555,
+  "estimated_cost_usd": 0.2644225,
   "cost_status": "estimated",
   "cost_source": "provider_models_api",
   "input_tokens": 2,
-  "output_tokens": 1781,
-  "cache_read_tokens": 20016,
-  "cache_write_tokens": 33826,
-  "reasoning_tokens": 298,
-  "total_tokens": 55625,
+  "output_tokens": 1775,
+  "cache_read_tokens": 0,
+  "cache_write_tokens": 35206,
+  "reasoning_tokens": 238,
+  "total_tokens": 36983,
   "api_calls": 1,
   "model": "anthropic/claude-opus-5",
   "provider": "openrouter",
-  "session_id": "20260731_225817_5a835f",
+  "session_id": "20260731_231137_f0e9a5",
   "completed": true,
   "failed": false,
   "service_tier": null
diff --git a/docs/showcase/devmemory-dogfood-torii/meta.env b/docs/showcase/devmemory-dogfood-torii/meta.env
index 9ecf38c..7bc43bd 100644
--- a/docs/showcase/devmemory-dogfood-torii/meta.env
+++ b/docs/showcase/devmemory-dogfood-torii/meta.env
@@ -1,5 +1,5 @@
-RUN_ID=run-20260731T225816-aeecec
+RUN_ID=run-20260731T231135-bf6235
 SESSION_ID=dogfood-torii-session
 SESSION_SOURCE=file
 REPO_ROOT=/Users/ashishmishra/Documents/experiments/pr-review-agent
-ASSEMBLED_AT=2026-07-31T17:28:16Z
+ASSEMBLED_AT=2026-07-31T17:41:36Z
diff --git a/docs/showcase/devmemory-dogfood-torii/preview.diff b/docs/showcase/devmemory-dogfood-torii/preview.diff
index 9a133ac..aabc48f 100644
--- a/docs/showcase/devmemory-dogfood-torii/preview.diff
+++ b/docs/showcase/devmemory-dogfood-torii/preview.diff
@@ -1,11 +1,29 @@
+diff --git a/DEV.md b/DEV.md
+--- a/DEV.md
++++ b/DEV.md
+@@ -125,7 +125,6 @@
+ - `hermes -z` is not reliable: an observed `-z` rc=2 on odoo PR #2 forced the `hermes chat -q` path, which is exactly the polluted-output case F44 scrubs. Anything that assumes one-shot mode always wins will regress (tracked as H14).
+ - `tool_turns=0` on a multi-file PR is a quality smell for an *agentic* review product, not a cheap win: the no-tool mini run on PR #2 returned APPROVE while an earlier GHA tool-using review caught the real gap (missing `format:false` tests). **F45/H12** fail-closes: `scripts/tool_turns_gate.py` downgrades APPROVE→COMMENT, caps score at 55, injects an F45 banner, writes `tool-turns-gate.env` (chip `tool-turns-gate`). Docs-only / single-file exempt; `LUFFY_TOOL_TURNS_GATE=off` disables.
+ - **F49/H15 soft re-prompt:** same eligibility as F45, **once** before fail-closed — re-run `hermes -z` with a tool-nudge suffix (`reprompt-write`). Default on (`LUFFY_TOOL_TURNS_REPROMPT=1`). Evidence: `tool-turns-reprompt.env` + chips `tool-reprompt` / `tool-reprompt-ok`. If tools still 0, F45 still annotates. Doubles cheap-path spend when it fires — intentional recovery cost.
+-- **F50/H20 severity calibration:** when the review **self-reports** a test gap under **APPROVE**, `scripts/severity_calibration.py` upgrades to **REQUEST CHANGES**, caps score at 69 (override `LUFFY_SEVERITY_SCORE_CAP`), injects F50 banner, chip `sev-cal`. Default on (`LUFFY_SEVERITY_CALIBRATION=1`). Complements SOUL/prompt rules that missing tests for claimed production fixes are Blocking. Offline: odoo #2 F49 APPROVE 95→RC (GHA parity); #5 tests:no; #4 clean. Offline re-score without new OpenRouter spend via `severity_calibration.py apply` on an existing review.md.
+ - **F46/H13 SOUL load:** Hermes blocks context files matching threat patterns. Never quote classic injection phrases in `agent/SOUL.md`. Preflight: `scripts/soul_context_scan.py check`; runtime: `soul-context.env` + chip `soul-blocked`.
+ 
+ - The normalizer is a **trust boundary**, not a formatter: never accept a body as a valid review contract just because expected snippets/headings appear in it — prompt echo contains all of them. Contract checks must assert the placeholder-free form.
+@@ -158,3 +157,5 @@
+ - The script is designed for hermetic tests: `LUFFY_COOLDOWN_FIXTURE` supplies a JSON array of `{created_at, body}` comments (no network) and `NOW_EPOCH` pins the clock — see `tests/test_cooldown_check.py`.
+ 
+ - `scripts/apply-verdict-labels.py` follows the repo's plan/apply split: `plan` computes the label decision with no network, `apply` performs it. `LUFFY_LABELS_FIXTURE=path.json` makes `apply` **write the planned GitHub API operations to a file instead of invoking `gh`** — that seam is what lets `tests/test_apply_verdict_labels.py` cover the mutation path with no token and no live PR. Prefer this env-fixture pattern over mocking `subprocess` when adding new gh-calling scripts.
++
++- Prompt/contract changes are motivated by rubric evidence, not intuition: the 6-PR `torii-eval` corpus on `Mr-Ashish/odoo` is scored out of 50, and a low per-dimension score (here tool depth on eval #6: 34/50 with that dimension at 2) is what justifies a new feature flag such as F51. Each fix is then validated by a live mini re-score of the same PR under the new build.
+
 diff --git a/agent/DEV.md b/agent/DEV.md
 --- a/agent/DEV.md
 +++ b/agent/DEV.md
-@@ -26,6 +26,8 @@
+@@ -28,6 +28,8 @@
  
- - The required depth is concrete, not exhortative: read the diff hunks, then `rg` the changed symbols and read the surrounding **line range** in the changed file. Reading a large file with `head` only is explicitly forbidden, so "I looked at the file" no longer counts as inspection.
+ - It shifts the objective from *whether* the reviewer used tools (F45/F49) to *how deeply* it looked, which is why it ships as prompt text plus an assertion in the existing tool-turns suite rather than a new post-review gate script.
  
-+- It shifts the objective from *whether* the reviewer used tools (F45/F49) to *how deeply* it looked, which is why it ships as prompt text plus an assertion in the existing tool-turns suite rather than a new post-review gate script.
++- The depth requirement is stated on three surfaces that must stay in sync: `build_reprompt_suffix` (F49 re-prompt text), the **Workspace** section of `agent/review-prompt.md`, and the **Scope** section of `agent/SOUL.md`. Changing the wording in only one place leaves the other two contradicting it.
 +
  ## Pitfalls
  
diff --git a/docs/showcase/devmemory-dogfood-torii/preview.json b/docs/showcase/devmemory-dogfood-torii/preview.json
index 656abce..42edaef 100644
--- a/docs/showcase/devmemory-dogfood-torii/preview.json
+++ b/docs/showcase/devmemory-dogfood-torii/preview.json
@@ -1,11 +1,17 @@
 {
   "stats": {
-    "files": 1,
-    "lines_added": 2,
-    "lines_removed": 0,
-    "changes": 1
+    "files": 2,
+    "lines_added": 4,
+    "lines_removed": 1,
+    "changes": 2
   },
   "files": [
+    {
+      "path": "DEV.md",
+      "is_new": false,
+      "lines_added": 2,
+      "lines_removed": 1
+    },
     {
       "path": "agent/DEV.md",
       "is_new": false,
diff --git a/docs/showcase/devmemory-dogfood-torii/prompt.md b/docs/showcase/devmemory-dogfood-torii/prompt.md
index c530888..c4d779b 100644
--- a/docs/showcase/devmemory-dogfood-torii/prompt.md
+++ b/docs/showcase/devmemory-dogfood-torii/prompt.md
@@ -106,24 +106,6 @@ agent
 ### git status
 ```
 M USAGE.md
- M agent/DEV.md
- M docs/showcase/devmemory-dogfood-torii/README.md
- M docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.json
- M docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.md
- M docs/showcase/devmemory-dogfood-torii/agent-loop/agent.log
- M docs/showcase/devmemory-dogfood-torii/agent-loop/usage.json
- M docs/showcase/devmemory-dogfood-torii/apply.json
- M docs/showcase/devmemory-dogfood-torii/extract.raw.md
- M docs/showcase/devmemory-dogfood-torii/hermes-usage.json
- M docs/showcase/devmemory-dogfood-torii/meta.env
- M docs/showcase/devmemory-dogfood-torii/preview.diff
- M docs/showcase/devmemory-dogfood-torii/preview.json
- M docs/showcase/devmemory-dogfood-torii/prompt.md
- M docs/showcase/devmemory-dogfood-torii/repo-context.md
- M docs/showcase/devmemory-dogfood-torii/session.md
- M docs/showcase/devmemory-dogfood-torii/summary.md
- M docs/showcase/devmemory-dogfood-torii/timings.json
- M docs/showcase/devmemory-dogfood-torii/units.json
 ?? .torii-out-e2e-pr2-f44/
 ?? .torii-out-e2e-pr2-f49/
 ?? .torii-out-e2e-pr2-h16/
@@ -131,15 +113,16 @@ M USAGE.md
 ?? .torii-out-e2e-pr4-h16/
 ?? .torii-out-e2e-pr5-f49/
 ?? .torii-out-e2e-pr6-f49/
+?? .torii-out-e2e-pr6-f51/
 ```
 
 ### recent log
 ```
+7070077 docs: mark F52 multi-lens worktree merged (PR #2)
+b774307 feat(review): F52 multi-lens checklist (H28) (#2)
+a5e26f1 docs(experiments): H27 F51 re-score #6 34→39/50
+083b223 dogfood: F51 tool-depth knowledge + showcase
 d27b477 feat(review): F51 tool-depth nudge after F49 (H26)
-0a201f0 docs(e2e): H24 score odoo#6 F49 mini 34/50 (tools 0→1 shallow)
-f67a963 docs(e2e): H23 corpus #6 odoo#279777 street_split → Mr-Ashish/odoo#6
-e9bb515 dogfood: F50 severity calibration knowledge + showcase
-b075a74 F50/H20: severity calibration for missing-test self-reports
 ```
 
 ### tree (sample)
@@ -264,6 +247,7 @@ docs/experiments/2026-07-31-f48-soul-detect-scope.md
 docs/experiments/2026-07-31-f49-soft-reprompt.md
 docs/experiments/2026-07-31-f50-severity-calibration.md
 docs/experiments/2026-07-31-f51-tool-depth.md
+docs/experiments/2026-07-31-f52-multi-lens.md
 docs/experiments/2026-07-31-f9-inline-comments.md
 docs/experiments/2026-07-31-f9b-precise-anchors.md
 docs/experiments/2026-07-31-f9c-suggestions.md
@@ -274,6 +258,7 @@ docs/experiments/loop-idle-streak.txt
 docs/experiments/loop-no-work-streak.md
 docs/experiments/odoo-e2e-benchmark.md
 docs/experiments/odoo-e2e-learn.md
+docs/experiments/parallel-worktrees.md
 docs/blog/building-torii-agentic-pr-review.md
 docs/benchmarks/hermes-startup-latest.json
 docs/benchmarks/hermes-startup-latest.md
@@ -342,8 +327,6 @@ scripts/publish-run-to-hub.sh
 scripts/report-verdict.sh
 scripts/review-local.sh
 scripts/review-to-openui.py
-scripts/run-hermes-review.sh
-scripts/run-torii-review.sh
 ```
 
 ### git diff
@@ -362,619 +345,6 @@ index 10a1fca..2e75fca 100644
  ## Troubleshooting
  
  - Confirm which Torii version a target repo runs: read `.torii-install-stamp` (`mode=pack|caller`, `source_sha`) and compare with `git -C <torii-source> rev-parse --short HEAD`. A stale `source_sha` after a re-install means files were skipped — re-run with `--force`. For `mode=caller`, runtime tracks hub `main`, not the stamp alone.
-diff --git a/agent/DEV.md b/agent/DEV.md
-index 2783af7..bf3f23e 100644
---- a/agent/DEV.md
-+++ b/agent/DEV.md
-@@ -24,6 +24,8 @@
- - **F47/H14 iteration cap contract:** the `hermes` CLI exposes no `--max-turns` flag, so the cap is applied through Hermes-native channels only — `HERMES_MAX_ITERATIONS=<n>` in the environment and/or `agent.max_turns: <n>` in `$HERMES_HOME/config.yaml`. Never re-add a `--max-turns` argv path to `scripts/run-hermes-review.sh`.
- - Because Hermes argparse treats an unknown leading token as a subcommand, a bare `N` after `-z` is read as a command name, not a value — any future tuning knob must be an env var or config key, not a positional/flag pair on the `hermes -z` line.
- 
-+- The required depth is concrete, not exhortative: read the diff hunks, then `rg` the changed symbols and read the surrounding **line range** in the changed file. Reading a large file with `head` only is explicitly forbidden, so "I looked at the file" no longer counts as inspection.
-+
- ## Pitfalls
- 
- - Same anchoring applies to `**Score:** <int>[/100]` and `**Confidence:** low|medium|high` — score/confidence are parsed only for reporting, and a missed match yields empty strings rather than an error.
-@@ -43,3 +45,5 @@
- 
- - Zero tool turns on attempt 1 is the norm, not an anomaly, on live upstream-port PRs: repeated e2e runs (odoo#2, #4, #5) all recorded `tool_turns=0` before the F49 soft reprompt, which then recovered a real agentic loop (0→23, 0→9, 0→8). Treat a `tool_turns=0` first attempt as expected and check whether `LUFFY_TOOL_TURNS_REPROMPT=1` was set before suspecting a prompt/toolset regression.
- - Because the reprompt succeeds, the F45 tool-turns gate reports *skipped* rather than pass/fail on these runs — a skipped F45 plus `soul_blocked=0` is the healthy signature, so do not read "gate skipped" as "gate not wired up".
-+
-+- Prompt-only mitigations like F51 need a live re-score to be believed — the shipped commit only proves the wording and tests changed, not that depth improved.
-diff --git a/docs/showcase/devmemory-dogfood-torii/README.md b/docs/showcase/devmemory-dogfood-torii/README.md
-index e19d2b7..bbe7466 100644
---- a/docs/showcase/devmemory-dogfood-torii/README.md
-+++ b/docs/showcase/devmemory-dogfood-torii/README.md
-@@ -1,4 +1,4 @@
--# Showcase · `run-20260731T224118-f42fe6`
-+# Showcase · `run-20260731T225742-823739`
- 
- Live dogfood run of **devmemory on itself**.
- 
-@@ -6,7 +6,7 @@ Live dogfood run of **devmemory on itself**.
- |-------|-------|
- | model | `anthropic/claude-opus-5` |
- | hermes_rc | 0 |
--| units | 4 |
-+| units | 3 |
- 
- ## Files
- 
-diff --git a/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.json b/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.json
-index 2e82088..8f4f1e0 100644
---- a/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.json
-+++ b/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.json
-@@ -1,33 +1,33 @@
- {
--  "run_id": "run-20260731T224118-f42fe6",
-+  "run_id": "run-20260731T225742-823739",
-   "model": "anthropic/claude-opus-5",
-   "hermes_rc": 0,
--  "units": 4,
--  "summary": "The session shipped F50/H20 severity calibration: a post-review gate (scripts/severity_calibration.py) that upgrades APPROVE\u2192REQUEST CHANGES when the review body self-reports missing/insufficient tests, gated by LUFFY_SEVERITY_CALIBRATION (default on) with a score cap of 69 and a sev-cal pack chip. Offline re-scores of the odoo e2e corpus quantify the effect (#2 36\u219242/50, #5 37\u219240/50, #4 clean no-op).",
-+  "units": 3,
-+  "summary": "Session shipped F51, a tool-depth nudge layered on top of F49's soft re-prompt: the re-prompt suffix plus the review prompt's Workspace section plus SOUL's Scope section now require the reviewer to read diff hunks and rg/line-range the changed symbols, and forbid head-only reads of large files. Durable knowledge: the three-surface contract for tool-depth wording, the shallow-read failure mode that motivated it, and how to verify it.",
-   "usage": {
--    "estimated_cost_usd": 0.27356625,
-+    "estimated_cost_usd": 0.2573225,
-     "cost_status": "estimated",
-     "cost_source": "provider_models_api",
-     "input_tokens": 2,
--    "output_tokens": 2318,
-+    "output_tokens": 1657,
-     "cache_read_tokens": 0,
--    "cache_write_tokens": 34497,
--    "reasoning_tokens": 264,
--    "total_tokens": 36817,
-+    "cache_write_tokens": 34542,
-+    "reasoning_tokens": 204,
-+    "total_tokens": 36201,
-     "api_calls": 1,
-     "model": "anthropic/claude-opus-5",
-     "provider": "openrouter",
--    "session_id": "20260731_224120_31ac74",
-+    "session_id": "20260731_225744_1eb754",
-     "completed": true,
-     "failed": false,
-     "service_tier": null
-   },
-   "timings": {
--    "assemble_s": 0.666,
--    "extract_s": 30.615,
--    "normalize_s": 0.001,
--    "apply_s": 3.919,
--    "total_s": 35.208
-+    "assemble_s": 1.332,
-+    "extract_s": 23.518,
-+    "normalize_s": 0.002,
-+    "apply_s": 1.505,
-+    "total_s": 26.362
-   },
-   "messages_meta": {
-     "db": "/Users/ashishmishra/Documents/experiments/pr-review-agent/.devmemory/hermes-home/state.db",
-diff --git a/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.md b/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.md
-index 246880d..182fd81 100644
---- a/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.md
-+++ b/docs/showcase/devmemory-dogfood-torii/agent-loop/agent-loop.md
-@@ -1,31 +1,31 @@
--# Agent loop · `run-20260731T224118-f42fe6`
-+# Agent loop · `run-20260731T225742-823739`
- 
- - **model:** `anthropic/claude-opus-5`
- - **hermes_rc:** 0
--- **units:** 4
--- **at:** 2026-07-31T17:11:54Z
-+- **units:** 3
-+- **at:** 2026-07-31T17:28:08Z
- 

… [diff truncated] …
```

## existing knowledge files

### claim index (do not restate these claims)
- [DEV.md#Architecture] @torii action assemble cacheartifact checkout comment concurrency context
- [DEV.md#Architecture] artifact compos deterministic every inner llm-driven orchestr record
- [DEV.md#Architecture] anchor assemble-contextsh banner budget console contractfencessizehtml diff-trunc dismiss-prior
- [DEV.md#Architecture] --caller --with-hub-ingest --with-runner-build adoption agent agentscript default entrypoint
- [DEV.md#Architecture] branch checkout config default domain torii torii-hermes-home memory
- [DEV.md#Architecture] caller concurrency f10 githubworkflowstorii-review-reusableyml input issuecomment torii-pr-reviewyml toriiref
- [DEV.md#Design decisions] action append comment complet console deep-link f35 footer
- [DEV.md#Design decisions] 422 actually added chang comment f9b f9f9b findingsblock
- [DEV.md#Design decisions] authoriz bearerx-torii-token escape f33f34 f34 fail-clos github hmac-sha256
- [DEV.md#Design decisions] --bit --spawn browser command console default dry-plan enqueue
- [DEV.md#Design decisions] --soft action artifact auto-detect bundle download f31 failur
- [DEV.md#Design decisions] action cache container detect dockertorii-runner ensureherm exist image
- [DEV.md#Design decisions] comment delet torii torii-review toriireplaceprevious=0 marker match prior
- [DEV.md#Design decisions] always-publish comment crash failure hermesmodel low-confidence openrouter produce
- [DEV.md#Design decisions] agentic assembl beyond capture-hermes-looppy completion default inspect toriitoolset
- [DEV.md#Design decisions] activity agenttool hermestuitoolprogress=verbose later level observability pythonunbuffered=1 recoverable
- [DEV.md#Design decisions] directory disposable explicitly hermeshome memory memorymd preserv through
- [DEV.md#Design decisions] $from chmod executable install install-toriish installer installupdate itself
- [DEV.md#Design decisions] --force avoid canonical explicitly half-cop install itself torii
- [DEV.md#Design decisions] append empty explicitly guard never no-op non-dict non-load-bear
- [DEV.md#Design decisions] --max-usd alert already budget estimat exceed f29 footerjob-summary
- [DEV.md#Design decisions] 15k10k10m absent artifact boolean deliberately download field footer
- [DEV.md#Design decisions] block caller contentspull-requestsissuesac declar every forget grant itself
- [DEV.md#Design decisions] contrac
… [claim index truncated; do not restate] …

### knowledge excerpts
### DEV.md

## Architecture
- Torii is a gated GitHub Actions control plane, not a chat bot: `@torii review this pr` → gate + per-PR concurrency → dual checkout → restore Hermes memory → assemble context → `hermes -z` → normalize → PR comment → distill memory → cache/artifacts.
- Orchestration is deterministic shell (`scripts/run-torii-review.sh` composes stages and records timings); only the inner review step is LLM-driven, so every run leaves reproducible artifacts.
- Stage → script map: assemble-context.sh (gh pr meta + diff + prompt, no LLM), run-hermes-review.sh (Hermes one-shot over `WORKSPACE_ROOT`; F7 pin via hermes-pin.sh), normalize-review.py (contract/fences/size/HTML marker + secret redact + F27 diff-truncation banner), usage-summary.py (F21 cost footer/job summary + F29 soft max budget), parse-verdict.py + report-verdict.sh (F22 reaction/status + F23 formal PR review + F24 dismiss-prior + F9 inline), post-inline-comments.py (F9 path anchors), distill-memory.sh, post-review-comment.sh, save-trace.sh, publish-run-local.sh (F28 `.torii/`), publish-run-to-hub.sh (opt-in), hub-ingest-run.py (hub + local layouts), pack-run-for-ui.py (F31 Run Console `run-bundle.json`, soft).
- **F20/F10 install:** `scripts/install-torii.sh` is the adoption entrypoint. Default **pack** mode copies `agent/`, runtime scripts, thin `torii-pr-review.yml`, and `torii-review-reusable.yml`. **`--caller`** installs only the hub-managed thin workflow from `pack/torii-pr-review-caller.yml` (no agent/scripts). Optional `--with-hub-ingest` / `--with-runner-build` (pack mode). Stamp `.torii-install-stamp` rec
… [truncated; do not restate] …

### ui/DEV.md

## Design decisions
- **Run Console** loads a single `run-bundle.json` (F31 pack) — operators never need raw Hermes logs for first triage.
- **Ops signals (F40+)** surface gates as chips + Overview rows: path-skip, timeout, over-budget, diff-truncated, max-turns (F41), model-tier (F42).
- **F42 model tier** chips (`model-cheap` / `model-full`) come from pack `signals` filled by `model-tier.env`; Overview shows mode/tier/reason + effective model id.
- **F43 preflight cost** chips (`preflight-cheap` / `preflight-refuse`) come from `preflight-cost.env` via pack signals — refuse means no Hermes spend; forced-cheap means estimate exceeded budget on the premium model.

## Pitfalls
- Fixture re-pack (`npm run pack-fixture`) must stay green after pack-run signal shape changes or Overview types drift.
- Empty `signals.flags` means either a clean paid run *or* tier mode was `off` — check `signals.model_tier_mode` before assuming auto-tier ran.

### ui/review-console/DEV.md

## Architecture
- The console renders `bundle.signals` in two places: header **chips** (shown only when at least one flag is set) and an **Ops signals (F40)** panel in the Overview tab — so a clean run stays visually quiet and any degraded run is visible without opening a tab.
- Phase tracker state: Phase 2 (standalone review console shell) is **superseded** by the full Run Console; F40 ("ops signals in console", phase 4d) is done, while **4c live progress streaming remains pending** — treat streaming as the next console workstream, not signals.
- Those metrics render in two places: an **Agent loop (F41)** panel in the Overview tab, and measures on the **Loop** tab — i.e. `loop` is a first-class bundle section alongside `signals`, not a sub-field of it.

## Design decisions
- **F50 `sev-cal`** joins the pack-signal chip family (path-skip, timeout, over-budget, diff-truncated, max-turns, model-tier, preflight, tool-turns): it means the severity-calibration gate rewrote the verdict to `REQUEST CHANGES` and capped the score at 69, so the displayed verdict/score may differ from what the model emitted — read the chip before trusting the raw review score.

### readme-kit/DEV.md

## Design decisions
- Config format: YAML is the preferred input with JSON kept at parity (`examples/torii/` ships both `readme.config.yaml` and `readme.config.json`), so either file shape drives the same build.
- YAML parsing uses the `yaml` npm dependency; the previously hand-rolled parser was deleted rather than kept as a fallback — do not reintroduce a bespoke parser for "zero-dep" reasons.

### docker/torii-runner/DEV.md

## Design decisions
- The image's job is to satisfy a two-signal contract that CI probes, not to run Torii itself: it sets `LUFFY_HERMES_PREBAKED=1` and writes the resolved SHA to `/root/.hermes-pin`, and bakes `PATH=/root/.local/bin:/root/.hermes/bin`. `ensure_hermes` short-circuits when either signal is present *and* `hermes` is on PATH, so a broken/renamed marker silently falls back to a cold install instead of failing loudly.
- Base is plain `ubuntu:24.04` plus the minimum Hermes needs (`ca-certificates curl git python3 python3-venv bash build-essential`); Hermes is installed at build time with `install.sh --skip-setup --commit "${HERMES_COMMIT}" --force-commit`, i.e. the same pinned, non-interactive install path CI uses (F7).
- The pin is an `ARG HERMES_COMMIT` with a hardcoded default that must track `scripts/hermes-pin.sh` DEFAULT — `scripts/build-torii-runner-image.sh` resolves the pin via `scripts/hermes-pin.sh default` (overridable with `HERMES_COMMIT=…`) and passes it as `--build-arg`, so the Dockerfile default only matters for raw `docker build` invocations.
- Tagging is pin-derived, not semver: `ghcr.io/<owner>/torii-hermes-runner:<first-12-chars-of-pin>` plus `:latest`, which makes the image ref self-documenting about which Hermes commit is inside.

### memory/DEV.md

## Architecture
- This repo doubles as the central hub: every target repo's run is ingested under `memory/repos/{owner}--{repo}/` (slug uses `--` to flatten owner/repo), holding `MEMORY.md`, `latest.json`, and a `runs/` history.
- Publish path: `build-hub-payload.py` produces a redacted, size-capped payload → `publish-run-to-hub.sh` (direct push by default, `repository_dispatch torii-run` optional) → `hub-ingest-run.py` commits under `memory/`.
- Hub memory is preloaded into `HERMES_HOME` at the start of each run (`preload-hub-memory.sh`), which is what makes the next review on the same repo smarter — memory is cross-run and cross-repo, not per-job.
- Hub behaviour is env-configurable per target repo: `LUFFY_HUB_REPO` (default `Mr-Ashish/torii-pr-review-agent`), `LUFFY_HUB_MODE` (`direct`|`dispatch`|`both`), `LUFFY_HUB_PUBLISH=0` to disable.

## Pitfalls
- Direct push therefore needs write on the hub: on the hub repo itself `GITHUB_TOKEN` + `contents: write` is sufficient (self-review), but any *other* target repo requires `LUFFY_HUB_TOKEN` (PAT with contents write on the hub) or hub publishing silently degrades.
- Original failure mode this layer exists to fix: hub memory was written after a run but **not loaded into** the next review — the preload step is the load half of the contract, and without it the `memory/` tree is write-only.
- `preload-hub-memory.sh` fetches `.torii/MEMORY.md` through the **default-branch contents API** (`api.github.com/repos/$REPO/contents/...`), not from the checked-out workspace: the PR checkout is sparse/PR-head, so reading it from disk would
… [truncated; do not restate] …

### modal_app/DEV.md

## Design decisions
- The Modal entrypoint is a first-class host in the F31 Run Console contract: `review_pr` exports `LUFFY_HOST=modal` so `pack-run-for-ui.py` stamps the bundle's host label as `modal` instead of falling through the `GITHUB_ACTIONS`/else auto-detect to `local`.
- `review_pr` also returns the `run_bundle` path in its result, so a Modal caller gets the console bundle handle back directly rather than having to download an Actions artifact (the GHA path's only option).
- F34 deliberately reverses F33's behaviour rather than extending it: F33 allowed unauthenticated requests with a warning when no secret/token was configured; F34 makes that same state `auth=denied` so the production-safe posture is the default and misconfiguration is loud instead of silent.
- The open-mode escape hatch is exposed on three surfaces that must stay in sync: env `LUFFY_WEBHOOK_ALLOW_OPEN=1`, the `allow_open=True` argument on the auth helper, and the `--allow-open` flag on `scripts/webhook_auth.py`. All three exist for dev/self-check only — none is a supported production configuration.

## Architecture
- Bit 4 (F32) splits the enqueue path into four units in `modal_app/app.py`: `parse_enqueue_payload` (normalize an incoming request into repo/pr/model/post_comment), `plan_enqueue` (pure plan, no side effects), `enqueue_review` (the spawn call), and `review_webhook` (the HTTP entrypoint). Parsing/planning are separable from spawning so the parser can be self-checked without any OpenRouter spend.
- `review_webhook` accepts two payload shapes: the simple API `{repo, pr, model, post_comm
… [truncated; do not restate] …

### pack/DEV.md

## Architecture
- `pack/` holds installable templates that are *not* live workflows in this repo: `torii-pr-review-caller.yml` is the F10 hub-managed thin caller, copied verbatim to `.github/workflows/torii-pr-review.yml` on the target by `install-torii.sh --caller`.
- It differs from this repo's own `torii-pr-review.yml` in exactly one way: `uses:` is the absolute hub ref `Mr-Ashish/torii-pr-review-agent/.github/workflows/torii-review-reusable.yml@main` with literal `torii_repository`/`torii_ref` values, instead of the local `./.github/workflows/...` path with `github.repository`.
- Triggers, `permissions`, and the `torii-${{ github.repository }}-<pr>` concurrency group are duplicated in the template because a `workflow_call` job cannot own them — edits to gating must be applied to `pack/torii-pr-review-caller.yml` as well as the in-repo caller.

## Design decisions
- Pack-mode install now seeds the target's `.torii/MEMORY.md` (`seed_local_memory()` in `install-torii.sh`), copying `agent/MEMORY.seed.md` when present and falling back to an inline stub. It honours `--force` (skips an existing file otherwise) and `--dry-run`, and runs before `write_stamp "pack"`.
- `--caller` (hub-managed thin) installs **do not** seed `.torii/` because no agent/scripts are copied — the installer instead prints a tip to seed `.torii/MEMORY.md` manually on the default branch (or run pack mode once). A caller repo with no seed simply starts from `MEMORY_SOURCE=seed`.
- Regression coverage lives in `tests/test_install_torii.py`: pack install asserts both `scripts/publish-run-local.sh` and `.luff
… [truncated; do not restate] …

### agent/DEV.md

## Design decisions
- `agent/SOUL.md` is the reviewer contract: staff-level reviewer scoped to *this diff's* added lines, explicitly told it sees partial hunks and must not invent missing imports or re-suggest changes already in the `+` lines.
- Trust model lives in SOUL, not in the prompt template: PR text and diff are UNTRUSTED DATA; author text that redefines the task or forces a merge verdict must be refused.
- Finding discipline is asymmetric by design: thorough on bugs/security, high bar elsewhere — every finding needs file + symbol + concrete trigger, and silence beats speculation (an empty Blocking section is an acceptable output).
- Every review must emit structured judgment fields: Score 0–100, review effort 1–5, security audit verdict, relevant-tests yes/no, key findings, optional concrete code suggestions.

## Pitfalls
- Same anchoring applies to `**Score:** <int>[/100]` and `**Confidence:** low|medium|high` — score/confidence are parsed only for reporting, and a missed match yields empty strings rather than an error.
- `UNKNOWN` is deliberately non-blocking (reaction `eyes`, status `success`, review_event `COMMENT`), so a broken prompt contract looks like a healthy neutral review instead of failing loudly. Verify the posted body still carries the bold verdict line after any prompt/template edit.
- F23 dual-channel: the full Markdown is still the issue comment (F12 replace via `<!-- torii-review pr=N`); the formal PR Review body is intentionally short so the Reviews panel is not a second full dump. Marker `<!-- torii-pr-review pr=N` tags Torii-owned PR reviews.

… [truncated; do not restate] …

### USAGE.md

## Run console
- **F31 auto-pack:** every review writes `.torii-out/run-bundle.json` (and `traces/<id>/run-bundle.json`) — download the `torii-out` or `torii-trace` Actions artifact and load it in the console. Soft-fail only.
- **F40–F49 signals:** bundle includes `signals` (timeout / path-skip / over-budget / diff-truncated / max-turns / model-tier / preflight / **tool-turns-gate** / **tool-turns-reprompt** + `flags[]`) and `loop` metrics. Overview shows **Ops signals** + **Agent loop (F41)**; header chips when any flag is set. Path-skip → `ops-signals.env`; F41 → `hermes-max-turns.env`; F42 → `model-tier.env`; F45 → `tool-turns-gate.env`; F49 → `tool-turns-reprompt.env`.
- Manual pack (showcase / older runs): `python3 scripts/pack-run-for-ui.py --dir path/to/run-or-showcase -o run-bundle.json` (`--host gha|modal|local`, `--memory-health path`, `--also path`, `--soft`).
- UI: `cd ui/review-console && npm install && npm run pack-fixture && npm run dev` → http://localhost:5177 → **Load bundle** for any `run-bundle.json`.

## Trigger a review (F32)
--model anthropic/claude-opus-5 --diff-bytes 200000 --file-count 20
--path a.js --path b.js --env-out tool-turns-gate.env
**before** F45 fail-closed. Attempt-1 artifacts are kept under
--prompt-in prompt.md --prompt-out prompt-reprompt.md \

## Common commands
- Install Torii into another repo (self-contained pack): `./scripts/install-torii.sh /path/to/target-repo` (`--force` overwrite; `--dry-run` preview).
- Hub-managed thin install (F10, no agent/scripts copy): `./scripts/install-torii.sh --caller /path/to/target-repo`.
- Build 
… [truncated; do not restate] …

### docker/torii-runner/USAGE.md

## Setup
- Order of operations to adopt the prebaked runner: (1) publish the image (`PUSH=1 ./scripts/build-torii-runner-image.sh` or the **Build Torii Hermes runner** workflow), (2) make the GHCR package readable by Actions — public package, or explicitly grant the consuming repo access, (3) set repo variable `LUFFY_RUNNER_IMAGE` to the pin-tagged ref (e.g. `ghcr.io/mr-ashish/torii-hermes-runner:53559aaf86b8`), (4) re-trigger `@torii review`.
- The workflow resolves the container as `${{ vars.LUFFY_RUNNER_IMAGE != '' && vars.LUFFY_RUNNER_IMAGE || null }}`, so leaving the variable unset (or empty) is the supported default path: host `ubuntu-latest` + pin-keyed Hermes install cache. There is no separate on/off flag.
- Verify an image locally before wiring it into CI: `docker run --rm ghcr.io/mr-ashish/torii-hermes-runner:latest hermes --version`.

## Troubleshooting
- A stale `LUFFY_RUNNER_IMAGE` pin is invisible: the prebaked short-circuit returns before any pin comparison, so a container built from an older `HERMES_COMMIT` will run happily against a newer `scripts/hermes-pin.sh` default. Compare the image tag's 12-char pin against `scripts/hermes-pin.sh default` when Hermes behaviour differs between the container path and the host path.
- Self-hosted runners can opt into the same fast path without the image by placing `hermes` on PATH plus a `/root/.hermes-pin` (or `$HOME/.hermes-pin`) marker file.

### modal_app/USAGE.md

## Common commands
- Bit 4 dry enqueue plan (no LLM spend, self-checks the payload parser): `modal run modal_app/app.py --bit 4 --repo Mr-Ashish/odoo --pr 3` → `BIT4_OK`.
- Actually enqueue the worker: append `--spawn` to the same command.
- Publish the webhook: `modal deploy modal_app/app.py`, then POST `{"repo":"Mr-Ashish/odoo","pr":3,"model":"openai/gpt-4.1-mini","post_comment":true}` to the `review_webhook` URL (or forward a GitHub `issue_comment` payload).
- F33/F34 auth: set `LUFFY_WEBHOOK_TOKEN` (`Authorization: Bearer …`) and/or `LUFFY_WEBHOOK_SECRET` (GitHub `X-Hub-Signature-256`). Fail-closed without either unless `LUFFY_WEBHOOK_ALLOW_OPEN=1`. Helper: `python3 scripts/webhook_auth.py sign|authorize [--allow-open]`.

## Debugging
- If a live POST is rejected, reproduce locally first: `python3 scripts/webhook_auth.py sign` to mint an `X-Hub-Signature-256` over the exact raw body, then `python3 scripts/webhook_auth.py authorize` to see which branch fired, rather than guessing from the Modal response.
- Modal profile version `0.6.0-f39` (F39 host parity): path-skip before clone + report-verdict after review. Quote it when comparing behaviour across deployed revisions.
- Path-skip offline: `python3 scripts/modal_parity.py path-skip --path README.md --globs docs` → exit 2 means Modal would skip OpenRouter.
- F41: `LUFFY_MAX_TURNS` (default 40) caps Hermes tool iterations on Modal; set `0`/`off` to disable. App version `0.6.1-f41`.

