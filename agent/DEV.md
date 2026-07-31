# DEV — engineering knowledge

> How this part of the system is built.

## Design decisions

- `agent/SOUL.md` is the reviewer contract: staff-level reviewer scoped to *this diff's* added lines, explicitly told it sees partial hunks and must not invent missing imports or re-suggest changes already in the `+` lines.
- Trust model lives in SOUL, not in the prompt template: PR text and diff are UNTRUSTED DATA; author text that redefines the task or forces a merge verdict must be refused.
- Finding discipline is asymmetric by design: thorough on bugs/security, high bar elsewhere — every finding needs file + symbol + concrete trigger, and silence beats speculation (an empty Blocking section is an acceptable output).
- Every review must emit structured judgment fields: Score 0–100, review effort 1–5, security audit verdict, relevant-tests yes/no, key findings, optional concrete code suggestions.
- Output contract is a single bare Markdown document (no preamble, no tool chatter, not fence-wrapped) so `normalize-review.py` can validate and post it directly as a PR comment.

- Verdict text is normalized rather than required to be exact: aliases map `APPROVED`/`LGTM` → `APPROVE`, `REQUEST_CHANGES`/`REQUEST-CHANGES`/`CHANGES REQUESTED` → `REQUEST_CHANGES`, `COMMENTS`/`NEUTRAL` → `COMMENT`; whitespace is collapsed, trailing `.` stripped, and any trailing parenthetical/bracket note removed.
- After exact-alias lookup there is a prefix pass, so decorated verdicts like `REQUEST CHANGES — see blocking` still resolve. This tolerance is intentional: the model is allowed prose after the token, but not allowed to move the label off the line start.

- F9b splits the precise-anchor feature across prompt and script: the model side is `agent/SOUL.md` rule 10 ("when a defect is on a specific **new** line you saw in the diff, cite `path:LINE`") plus the `agent/review-prompt.md` Key findings **File** column preferring `path:LINE` when the line is visible in the diff. Without those two, `scripts/post-inline-comments.py` has no `line_hint` to consume and always degrades to the F9 nearest/first anchor.
- The citation rule is deliberately scoped to **new** (`+`) lines only, matching the reviewer's added-lines scope — a `path:LINE` pointing at unchanged context is not a usable anchor for a GitHub review comment.

- The SOUL's *optional* **Code suggestions** field is now load-bearing downstream: F9c turns each `#### title (`path`)` + ```diff``` block into a GitHub apply-suggestion comment, so the section's shape (heading with backticked path, diff fence with `-`/`+` lines that mirror real PR lines) is a machine contract, not free-form prose.
- Consequence for prompt/SOUL edits: changing how suggestions are formatted, or encouraging suggestions against unchanged context, degrades F9c to zero posted apply blocks without any error — the reviewer instruction "only when you can show a concrete better snippet for **new** code" is what keeps suggestions anchorable.

- The cap is applied to the *disposable* `HERMES_HOME` config that `run-hermes-review.sh` rewrites per run, so `agent/config.yaml` is the template, not the live file the agent reads.

- **F47/H14 iteration cap contract:** the `hermes` CLI exposes no `--max-turns` flag, so the cap is applied through Hermes-native channels only — `HERMES_MAX_ITERATIONS=<n>` in the environment and/or `agent.max_turns: <n>` in `$HERMES_HOME/config.yaml`. Never re-add a `--max-turns` argv path to `scripts/run-hermes-review.sh`.
- Because Hermes argparse treats an unknown leading token as a subcommand, a bare `N` after `-z` is read as a command name, not a value — any future tuning knob must be an env var or config key, not a positional/flag pair on the `hermes -z` line.

- The required depth is concrete, not exhortative: read the diff hunks, then `rg` the changed symbols and read the surrounding **line range** in the changed file. Reading a large file with `head` only is explicitly forbidden, so "I looked at the file" no longer counts as inspection.

- It shifts the objective from *whether* the reviewer used tools (F45/F49) to *how deeply* it looked, which is why it ships as prompt text plus an assertion in the existing tool-turns suite rather than a new post-review gate script.

- The depth requirement is stated on three surfaces that must stay in sync: `build_reprompt_suffix` (F49 re-prompt text), the **Workspace** section of `agent/review-prompt.md`, and the **Scope** section of `agent/SOUL.md`. Changing the wording in only one place leaves the other two contradicting it.

- F51 tool depth (H26) layers on top of the F49 soft re-prompt: F49 fixed whether the model used tools, F51 fixes how deeply it looked.
- The re-prompt suffix and reviewer contract now require reading actual diff hunks plus `rg` and line-range reading of each changed symbol.

## Pitfalls

- Same anchoring applies to `**Score:** <int>[/100]` and `**Confidence:** low|medium|high` — score/confidence are parsed only for reporting, and a missed match yields empty strings rather than an error.
- `UNKNOWN` is deliberately non-blocking (reaction `eyes`, status `success`, review_event `COMMENT`), so a broken prompt contract looks like a healthy neutral review instead of failing loudly. Verify the posted body still carries the bold verdict line after any prompt/template edit.
- F23 dual-channel: the full Markdown is still the issue comment (F12 replace via `<!-- torii-review pr=N`); the formal PR Review body is intentionally short so the Reviews panel is not a second full dump. Marker `<!-- torii-pr-review pr=N` tags Torii-owned PR reviews.

- **F41 max_turns:** `agent/config.yaml` sets `agent.max_turns: 40` (Hermes default 500 is unsafe for CI). Override with `TORII_MAX_TURNS`; `scripts/max_turns.py` resolves/detects budget hits.

- **F42:** `run-hermes-review.sh` may select cheap vs full model via `scripts/model_tier.py` when `TORII_MODEL_TIER=auto` (docs/tiny → cheap). Does not change SOUL/prompt content.

- **F43:** preflight cost may skip Hermes or force cheap model when `TORII_MAX_COST_USD` is tight — SOUL/prompt unchanged; stub review is COMMENT.

- `agent/SOUL.md` is scanned by Hermes context-file threat patterns before load; **F46/H13** rephrased the trust model so classic injection quotes do not false-positive. Guard with `python3 scripts/soul_context_scan.py check`. Runtime block still surfaces as `soul-context.env` + pack chip `soul-blocked`.

- Consequence: the **F45 tool-turns gate stays required** on multi-file code PRs whenever `tool_turns=0` (gate → `COMMENT` / confidence 55). Live re-score on `Mr-Ashish/odoo#2` with `openai/gpt-4.1-mini` held at 30/50 — the residual gap is tool use, not the CLI invocation.
- Open follow-ups for the cheap multi-file path: a soft re-prompt (H15) or a hard tool nudge (H18); do not remove the F45 gate before one of those lands.

- Zero tool turns on attempt 1 is the norm, not an anomaly, on live upstream-port PRs: repeated e2e runs (odoo#2, #4, #5) all recorded `tool_turns=0` before the F49 soft reprompt, which then recovered a real agentic loop (0→23, 0→9, 0→8). Treat a `tool_turns=0` first attempt as expected and check whether `TORII_TOOL_TURNS_REPROMPT=1` was set before suspecting a prompt/toolset regression.
- Because the reprompt succeeds, the F45 tool-turns gate reports *skipped* rather than pass/fail on these runs — a skipped F45 plus `soul_blocked=0` is the healthy signature, so do not read "gate skipped" as "gate not wired up".

- Prompt-only mitigations like F51 need a live re-score to be believed — the shipped commit only proves the wording and tests changed, not that depth improved.

- A non-zero tool-turn count is not evidence of real read: the F49 recovery case showed 0→1 tool turns, but the single call was `head -80` on a large module and the changed function was never read.
- Treat "tools used" and "changed symbol actually read" as separate signals when triaging shallow reviews.
