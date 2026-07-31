# Hermes-inspired ROI list (living)

Ideas scanned from read-only clones:
- `/tmp/hermes-agent` (NousResearch/hermes-agent)
- `/tmp/hermes-agent-self-evolution`

Only ship what fits Torii’s control-plane (scripts/agent/workflows/modal/ui) — do **not** fork Hermes into this repo.

| ID | Idea | Effort | Why ROI for Torii PR ops | Status |
|----|------|--------|--------------------------|--------|
| H1 | Cap `agent.max_turns` / `--max-turns` (Hermes default 500) | S | Stops runaway tool loops burning OpenRouter under F36 wall-clock | **Shipped F41** |
| H2 | Surface agent-loop metrics (tool turns, messages) in run-bundle | S | Operators see thrash without opening agent-loop.md | **Shipped F41** (with H1) |
| H3 | Skill-file evolution (GEPA/DSPy) for review-prompt / SOUL | L | Quality over time; needs eval harness + spend | **Shipped F69** (Torii-native skills; not GEPA/DSPy) |
| H4 | Context compressor / history budget for huge monorepos | M | Cuts tokens after F27 truncation | backlog |
| H5 | Session/search memory over past PR traces (FTS5 pattern) | M | Better repo memory than append-only distill | backlog (partial: F69 trajectories) |
| H6 | Hard preflight spend estimate before Hermes | S | Refuse/force cheap model when diff huge + budget tight | **Shipped F43** |
| H7 | Auto model tier by PR size (cheap first) | S | Cost without quality loss on docs/tiny PRs | **Shipped F42** |
| H8 | Subagent fan-out for multi-file PRs | L | Parallel review streams; Modal cost + complexity | backlog |
| H9 | Trajectory packaging for offline eval datasets | M | Quality regressions measurable | **Shipped F69** ingest |
| H10 | Soft skill nudge mid-loop (“prefer fewer tools”) | M | Hermes skill nudge pattern; needs hermes hooks | **Shipped F69** soft nudge inject |
| **H11** | **Strip hermes chat chrome + reject prompt-template echo in normalizer** | **S** | **F44 e2e: chat -q posted Query+template; contract false-positive** | **Shipped F44** |
| **H12** | **Fail closed when tool_turns=0 on multi-file non-docs PR (COMMENT, not re-prompt)** | **S** | **#2 mini APPROVE missed known test gap; GHA/tools did not** | **Shipped F45** |
| **H13** | **SOUL.md hermes prompt_injection false-positive workaround** | **S** | **F44 log: SOUL blocked — review discipline may not load** | **Shipped F46** |
| **H14** | **Make hermes -z reliable; avoid chat -q fallback** | **S** | **-z rc=2 was bogus `--max-turns` CLI flag → chat path** | **Shipped F47** |
| **H15** | **Soft re-prompt once when tool_turns=0 + multi-file (before F45 annotate)** | **M** | **Recover quality without always failing closed; evidenced on #2/#4/#5** | **Shipped F49** + live #2 0→23 + #4 0→9 + **#5 0→8** |
| H16 | Live re-score #2 mini after F47 (-z tools + F46 SOUL) | S | Measure D1/D8 lift vs F44/F45 rows | **Done H16** (total 30; -z ok; tools still 0) |
| **H17** | **Scope SOUL/max-turns detect + agent.log capture to this-invocation log offset** | **S** | **H16: stale agent.log → false soul_blocked=1** | **Shipped F48** |
| H18 | Hard tool nudge / require ≥1 workspace read on multi-file code PRs | S–M | First-pass still 0 tools on mini; F49 recovers — optional cost win | **P2 optional** (F49 live ok) |
| H19 | Live F49 re-score #4 multi-module PERF | S | Confirm recovery + lift 31→38 on 7-file stock/mrp | **Done H19** (38/50; 0→9 tools) |
| **H20** | **Severity calibration: missing tests → blocking when issue claims fix** | **S** | **F49 #2 APPROVE 95 vs GHA REQUEST CHANGES on alias tests** | **Shipped F50** + offline #2/#5 |
| H22 | Live F49 mini e2e + score odoo#5 (POS ticket screen) | S | Fresh corpus member needs baseline dims | **Done H22** (37/50; 0→8 tools) |
| H21 | Source 5th complex odoo/odoo PR → torii-eval corpus | S | Keep multi-PR evidence growing; prefer multi-module | **Done H21** (#5 odoo#279360) |
| H23 | Source 6th+ complex odoo/odoo PR → torii-eval corpus | S | Keep multi-PR evidence growing beyond 5 | **Done H23** (#6 odoo#279777) |
| H24 | Live F49 mini e2e + score odoo#6 (street_split) | S | Fresh corpus member needs baseline dims (+ F50 if test-gap) | **Done H24** (34/50; 0→1 tools) |
| H25 | Source 7th+ complex odoo/odoo PR → torii-eval corpus | S | Keep multi-PR evidence growing beyond 6 | backlog |
| **H26** | **Tool-depth after F49: nudge read changed hunks not file heads** | **S** | **#6 0→1 with head-only missed street_split region; D8=2** | **Shipped F51** + **H27 verified** |
| H27 | Live F51 mini re-score odoo#6 (street_split tool depth) | S | Measure D1/D8 lift vs H24 34/50 head-only | **Done H27** (39/50; 0→17 tools; +5 vs H24) |
| **H28** | **Multi-lens checklist (single-pass security/tests/perf/API/…) ** | **S** | **D10 multi-lens thin after F51; PRODUCT_FEATURE** | **Shipped F52** (prompt+SOUL+normalize) |
| H29 | Structured findings schema (severity+confidence+hunk cite) | S–M | Actionability + trust; merge multi-lens | backlog |
| **H30** | **Linked issue context (Fixes/#N → gh issue title/body/comments)** | **S** | **D8 claim-to-fix; pr-agent ticket compliance pattern** | **Shipped F53** |

## Selection rule

Each fire: pick **one** unfinished highest-ROI **minimal** item. Prefer S over M/L. Prefer cost/trust/ops over docs.

## Last pick

**H1+H2 → F41** (2026-07-31): wire Hermes iteration budget default 40 + loop metrics in pack/UI.

**H7 → F42** (2026-07-31): auto model tier (`TORII_MODEL_TIER=auto`) — cheap for tiny/docs, full otherwise.

**H6 → F43** (2026-07-31): hard preflight cost estimate — force_cheap then refuse when still over budget.

**H11 → F44** (2026-07-31): normalizer extracts real review from hermes chat chrome; rejects placeholder verdict / template echo; promotes loose headings for parse-verdict.

**H12 → F45** (2026-07-31): `tool_turns_gate.py` fail-closed — zero tools + multi-file non-docs → downgrade APPROVE→COMMENT, score cap 55, F45 banner; pack chip `tool-turns-gate`.

**H13 → F46** (2026-07-31): rephrase `agent/SOUL.md` trust model (no classic injection quotes); `soul_context_scan.py` preflight + log detect; pack chip `soul-blocked`.

**H14 → F47** (2026-07-31): stop passing `--max-turns` on `hermes` CLI (argparse has no flag → `invalid choice: 'N'` → chat fallback). Cap via `HERMES_MAX_ITERATIONS` + `agent.max_turns` config only; skip chat fallback on CLI argv rejection (`hermes-cli-argv.env`).

**H16** (2026-07-31): live mini re-run #2 post-F47 — `-z` ok, F45 gate, score 30/50, tools still 0.

**H17 → F48** (2026-07-31): `HERMES_LOG_OFFSET` into capture; this-invocation agent.log slice; stop SOUL detect on shared errors.log history.

**Corpus #4** (2026-07-31): port odoo#279776 → Mr-Ashish/odoo#4; mini score 31/50; F48 verified `soul_blocked=0`; tool_turns=0 again → H15 still P0.

**H15 → F49** (2026-07-31): soft re-prompt once on zero-tool multi-file code PRs before F45. `reprompt-decide`/`reprompt-write` + second `hermes -z`; `tool-turns-reprompt.env` + chips. F45 still fail-closes if attempt-2 also 0 tools.

**F49 live #2** (2026-07-31): `.torii-out-e2e-pr2-f49` — recovered tool_turns **0→23**; score **36/50** (H16 was 30); F45 skipped; ~$0.063. H18 demoted; **H19** (#4 F49 re-run) is next.

**H21 corpus #5** (2026-07-31): ported odoo#279360 → [Mr-Ashish/odoo#5](https://github.com/Mr-Ashish/odoo/pull/5) (6 files POS+restaurant).

**H22 F49 #5** (2026-07-31): `.torii-out-e2e-pr5-f49` — recovered tool_turns **0→8**; score **37/50**; F45 skipped; ~$0.028 · 56s; soul_blocked=0. All 5 corpus PRs scored.

**H20 → F50** (2026-07-31): `severity_calibration.py` — APPROVE + self-reported test gap → REQUEST CHANGES (score cap 69) + SOUL/prompt rules. Offline: #2 F49 36→**42**/50; #5 F49 37→**40**/50; #4 no-op. Chip `sev-cal`. **Next: H23** 6th upstream complex PR (or live F50 mini re-run).

**H23 corpus #6** (2026-07-31): ported odoo#279777 → [Mr-Ashish/odoo#6](https://github.com/Mr-Ashish/odoo/pull/6) (14 files: street_split regex + base_address_extended tests + l10n_dk_* fixtures; +138/−100). **Next: H24** F49 mini e2e + score #6.

**H24 F49 #6** (2026-07-31): `.torii-out-e2e-pr6-f49` — recovered tool_turns **0→1**; F50 no-op; APPROVE 95; ~$0.005 · 32s; score **34/50**. Weakest F49 depth (head-only). **Next: H26** tool-depth nudge or **H25** 7th upstream.

**H26 → F51** (2026-07-31): tool-depth nudge — F49 re-prompt suffix + `review-prompt.md` Workspace + SOUL Scope forbid `head`-only large-file reads; require diff hunks / `rg`+line-range on changed symbols. Tests green; SOUL preflight clean.

**H27** (2026-07-31): live F51 mini re-score #6 — `.torii-out-e2e-pr6-f51`; tool_turns **0→17**; `rg`+`sed -n 1940,1980p` on street_split; score **39/50** (H24 was 34); ~$0.034 · 18 API · 80s. **Next: H28** multi-lens PRODUCT_FEATURE or **H25** 7th upstream corpus PR.

**H28 → F52** (2026-07-31): multi-lens checklist in review template + SOUL + normalize soft section. Single-pass (no fan-out). **Next:** live re-score for D10 or H25 7th corpus PR.

**H30 → F53** (2026-07-31): linked issue context — extract Fixes/#N (+ URL/cross/branch), fetch via `gh` or fixture, inject into assemble prompt/context; chip `issue-ctx`; toggle `TORII_ISSUE_CONTEXT`. **Next:** live e2e on issue-linked eval PR for D8, or H25 7th corpus, or next product (filler / incremental / thread / testplan).
