# Odoo multi-PR e2e learn log

Target fork: [Mr-Ashish/odoo](https://github.com/Mr-Ashish/odoo) (upstream odoo/odoo).  
Local clone: `/Users/ashishmishra/Documents/experiments/odoo` → `odoo-torii-e2e`.  
Torii SoT: this repo only.

## Corpus (torii-eval PRs)

| PR | Title | Upstream | Files | +/− | Status |
|----|-------|----------|------|-----|--------|
| [#1](https://github.com/Mr-Ashish/odoo/pull/1) | torii-eval: #273306 website_cf_turnstile form callback guards | odoo#273306 / PR ~279479 | 1 JS | +12/−5 | OPEN |
| [#2](https://github.com/Mr-Ashish/odoo/pull/2) | torii-eval: #276570+#275937 web getFieldsSpec + format:false | issues 276570, 275937 | 4 (JS+test) | +85/−9 | OPEN |
| [#3](https://github.com/Mr-Ashish/odoo/pull/3) | torii-eval: #271153 tools Unicode XML control-char strip | odoo#271153 | 3 (py+test) | +88/−18 | OPEN |
| [#4](https://github.com/Mr-Ashish/odoo/pull/4) | torii-eval: #279776 stock, mrp replenishment horizon PERF | odoo#279776 | 7 (py+test) | +234/−22 | OPEN |
| [#5](https://github.com/Mr-Ashish/odoo/pull/5) | torii-eval: #279360 point_of_sale ticket screen responsiveness | odoo#279360 | 6 (JS/XML/SCSS) | +109/−122 | OPEN |
| [#6](https://github.com/Mr-Ashish/odoo/pull/6) | torii-eval: #279777 tools street_split regex + address fixtures | odoo#279777 | 14 (py+test+l10n fixtures) | +138/−100 | OPEN — F51 H27 **39/50** (was F49 34) |

Corpus size: **6** open eval PRs (all have ≥1 score row; #6 best = H27/F51).

## Runs

| When | PR | Run id | Model | Host | Notes |
|------|----|--------|-------|------|-------|
| 2026-07-30 | #1 | GHA 30558836212, 30559624590 | (workflow default) | Actions | REQUEST CHANGES — successCb null race |
| 2026-07-30 | #2 | GHA 30560489187 | (workflow default) | Actions | REQUEST CHANGES — missing format:false tests |
| 2026-07-30/31 | #3 | local + showcase | openai/gpt-4.1-mini + opus showcase | local | APPROVE 90; agentic-loop showcase |
| **2026-07-31 F44** | **#2** | **local / pr2-runlocal-a1** | **openai/gpt-4.1-mini** | local | hermes -z failed → chat -q; tool_turns=0; SOUL.md blocked as prompt_injection; raw polluted with Query+template; **F44 normalizer** extracts real body → APPROVE 90 (weaker than GHA: missed missing alias tests) |
| **2026-07-31 F45** | **#2** | **offline gate on F44 body** | n/a (post-process) | local | **H12/F45** re-apply: tool_turns=0 + 4 files → **APPROVE→COMMENT**, score 55, F45 banner; no new Hermes spend |
| **2026-07-31 H16** | **#2** | **local / pr2-runlocal-a1** (`.torii-out-e2e-pr2-h16`) | **openai/gpt-4.1-mini** | local | **F47 verify:** hermes `-z` rc=0 (no argv reject, no chat fallback); tool_turns=**0** (model text stop); F45→COMMENT/55; SOUL preflight clean; false `soul_blocked` from stale log → **F48** |
| **2026-07-31 corpus+4** | **#4** | **local / pr4-runlocal-a1** (`.torii-out-e2e-pr4-h16`) | **openai/gpt-4.1-mini** | local | Port odoo#279776; hermes `-z` ok; tool_turns=**0**; F45 APPROVE→COMMENT/55; **F48 soul_blocked=0** (clean); score **31/50** |
| **2026-07-31 F49 live** | **#2** | **local / pr2-runlocal-a1** (`.torii-out-e2e-pr2-f49`) | **openai/gpt-4.1-mini** | local | **F49 recovered:** tool_turns **0→23**; F45 skipped; APPROVE 95; ~$0.063 · 24 API · 95s; soul_blocked=0; chip `tool-reprompt-ok`; score **36/50** (was 30 H16) |
| **2026-07-31 H19 F49 #4** | **#4** | **local / pr4-runlocal-a1** (`.torii-out-e2e-pr4-f49`) | **openai/gpt-4.1-mini** | local | **F49 recovered:** tool_turns **0→9**; F45 skipped; APPROVE 95; ~$0.014 · 10 API · 58s; soul_blocked=0; chip `tool-reprompt-ok`; score **38/50** (was 31 post-F48) |
| **2026-07-31 H22 F49 #5** | **#5** | **local / pr5-runlocal-a1** (`.torii-out-e2e-pr5-f49`) | **openai/gpt-4.1-mini** | local | **F49 recovered:** tool_turns **0→8**; F45 skipped; APPROVE 92; ~$0.026 · 9 API · 56s; soul_blocked=0; chip `tool-reprompt-ok`; score **37/50** |
| **2026-07-31 F50 offline** | **#2/#5** | **post-process F49 bodies** | n/a | local | **H20/F50:** #2 APPROVE→REQUEST CHANGES (test gap in Suggestions); #5 tests:no → RC; #4 clean; scores **42** / **40** |
| **2026-07-31 H24 F49 #6** | **#6** | **local / pr6-runlocal-a1** (`.torii-out-e2e-pr6-f49`) | **openai/gpt-4.1-mini** | local | **F49 recovered:** tool_turns **0→1**; F45 skipped; F50 no-op; APPROVE 95; ~$0.005 · 2 API · 32s hermes; soul_blocked=0; shallow `head` only; score **34/50** |
| **2026-07-31 H27 F51 #6** | **#6** | **local / pr6-runlocal-a1** (`.torii-out-e2e-pr6-f51`) | **openai/gpt-4.1-mini** | local | **F51 depth:** tool_turns **0→17**; F45 skipped; F50 no-op; APPROVE 95; ~$0.034 · 18 API · 80s; soul_blocked=0; `rg`+`sed -n 1940,1980p` on street_split; score **39/50** (+5 vs H24) |

Artifacts: `.torii-out-e2e-pr2-f44/`; H16: `.torii-out-e2e-pr2-h16/`; #4: `.torii-out-e2e-pr4-h16/`; F49 #2: `.torii-out-e2e-pr2-f49/`; F49 #4: `.torii-out-e2e-pr4-f49/`; F49 #5: `.torii-out-e2e-pr5-f49/`; F49 #6: `.torii-out-e2e-pr6-f49/`; F51 #6: `.torii-out-e2e-pr6-f51/`.

## Introspect (F46)

1. **Root cause of SOUL block:** Hermes `threat_patterns` `prompt_injection` matched the literal quote `ignore previous instructions` in the trust-model examples — not a malicious SOUL.
2. **Fix is phrasing + regression scan:** product SOUL now clean under Hermes `scan_for_threats(scope=context)`; `soul_context_scan.py check` guards future regressions.
3. **Next P0:** H14 hermes `-z` reliability (chat fallback still forces F44 scrub + F45 gate path).

## Introspect (F45)

1. **Fail-closed without re-prompt is correct first step:** prevents false merge-green on zero-tool multi-file runs; does not invent the missing test finding (still needs tools / H14).
2. **Trust/ops win over signal quality:** D4/D9 improve via honesty; D1 still limited until agent actually reads files.
3. **Was next P0:** H13 SOUL.md prompt_injection — **shipped F46**.

## Introspect (F44)

1. **Chat fallback pollution (P0, fixed F44):** `hermes chat -q` echoes full prompt (including Markdown *template* with every required snippet). Pre-F44 normalizer treated that as contract-OK and would post the prompt to GitHub.
2. **Signal regression on cheap no-tool run:** GHA run correctly blocked on missing format-alias tests; gpt-4.1-mini with 0 tool turns APPROVE’d with medium “expand to other field types” noise instead.
3. **SOUL blocked:** hermes log `Context file SOUL.md blocked: prompt_injection` — review discipline may not load.
4. **Pin reinstall tax:** hermes pin mismatch forced full reinstall (~1–2 min) before the agent loop.
5. **Verdict parse** depends on `**Verdict:**`; chat mode often emits unbolded `Verdict:` — F44 promotes loose headings.

## Introspect (F47 / H14)

1. **Root cause of hermes -z rc=2:** Torii passed `--max-turns N` on the hermes CLI. Hermes has **no** such argparse flag; bare `N` is parsed as subcommand → `invalid choice: '25'` → exit 2 before any model call.
2. **Why chat fallback looked "successful" but tool_turns=0:** `hermes chat -q` accepts the bad argv more leniently (or ignores it) and runs a non-agentic single-shot with no workspace tools.
3. **Fix:** F47 removes CLI `--max-turns`; cap remains via `HERMES_MAX_ITERATIONS` + `agent.max_turns` config rewrite (Hermes-native). On CLI argv rejection, skip chat fallback (`hermes-cli-argv.env`) so we do not double-spend a zero-tool path.
4. **Next was H16** — done (see below).

## Introspect (H16 live mini + F48)

1. **F47 works:** H16 hermes stage 12s, stderr `hermes -z`, no `hermes-cli-argv.env`, session `20260731_215948_a52f62`, 1 API call, ~$0.003.
2. **tool_turns=0 is now a model problem:** with working `-z` + terminal toolset, gpt-4.1-mini still ended on first text response without reading workspace files — same false “tests complete” APPROVE body as F44, rescued only by F45.
3. **SOUL preflight true-clean; runtime soul_blocked was FP:** this-invocation `hermes-run.log` has no block line; full `HERMES_HOME/logs/agent.log` still contains older `SOUL.md blocked` from session `213006`. F48 scopes capture+detect to `HERMES_LOG_OFFSET`.
4. **Next P0:** H15 soft re-prompt or H18 hard tool nudge so multi-file cheap runs actually explore (restore D1 toward GHA).

## Introspect (corpus #4 / odoo#279776)

1. **Port clean:** `gh pr diff 279776` applied with zero conflicts onto Mr-Ashish/odoo@19.0 (7 files stock/mrp/purchase_mrp).
2. **Same cheap-path shape as #2 H16:** `-z` ok, F48 `soul_blocked=0`, still `tool_turns=0` → F45 COMMENT/55, soft rename nit only — multi-module PERF needs tools for real cache/correctness review.
3. **Corpus diversity win:** first multi-module backend PERF PR (vs web JS #1/#2 and pure tools #3).
4. **Reinforces H15/H18 P0:** second independent PR confirms tool skip is systemic on gpt-4.1-mini, not #2-specific.

## Introspect (F49 / H15)

1. **Soft re-prompt before F45:** recovery attempt is cheaper than inventing findings and honest if it fails (F45 still gates).
2. **Spend trade:** eligible multi-file zero-tool runs pay a second `hermes -z` (~2× cheap mini). Acceptable vs false APPROVE risk.
3. **Attempt-1 preserved:** `*.attempt1.raw.md` + `agent-loop-attempt1/` for A/B scoring.
4. **Live #2 verify:** recovered **0→23** tool turns; F45 skipped; D1 2→3 / total 30→36; still softer than GHA on missing alias-test severity.
5. **Attempt-1 still claims full coverage:** re-prompt is required for honesty on mini — not optional.

## Introspect (F49 live #2)

1. **H15 works end-to-end:** `tool-turns-reprompt.env` reason=`reprompt_recovered`; signals.flags=`tool-reprompt-ok`; gate reason=`tools_used`.
2. **Quality lift is real but incomplete:** agent used terminal/`rg` across web model + field widgets; soft-asks float `format:false` test; GHA still stronger (REQUEST CHANGES).
3. **Cost:** attempt-1 ~$0.002 + attempt-2 ~$0.063 ≈ 30× single-shot; still cheap vs full model; 95s wall.
4. **H18 demoted:** not P0 while recovery works; optional first-pass nudge to avoid double-run cost.
5. **Next:** F49 re-run #4 (7-file PERF); then optional 5th upstream PR; D9 severity calibration if #4 also soft-approves.

## Next learn targets

- **H26** tool-depth: re-prompt recovered but only 1 shallow `head` turn on #6 — nudge to read **changed line ranges** (not file heads).
- **H25** source 7th complex upstream PR.
- H18 optional (first-pass tools / cost); H20 shipped F50.

## Introspect (H19 / F49 live #4)

1. **F49 generalizes beyond #2:** On 7-file multi-module PERF, first pass still tool_turns=0; soft re-prompt recovered **0→9** (chip `tool-reprompt-ok`); F45 skipped.
2. **Score lift 31→38:** Tools enable real file/test reads; verdict APPROVE 95 with cache-comment suggestion is more grounded than zero-tool F45 COMMENT/55.
3. **Cheaper recovery than #2:** #4 attempt-2 ~$0.014 / 10 API / 58s vs #2 ~$0.063 / 24 API / 95s — recovery cost scales with tool thrash, not just file count.
4. **H18 still optional:** First-pass zero tools is model choice; F49 is enough for corpus; hard nudge is cost-optional only.
5. **Next was H21/H22** — corpus #5 + score.

## Introspect (corpus #5 / odoo#279360)

1. **Port clean:** `gh pr diff 279360` applied with zero conflicts onto Mr-Ashish/odoo@19.0 (6 files point_of_sale + pos_restaurant).
2. **Diversity:** multi-module POS frontend (JS/XML/SCSS) — complements web fields #2, tools #3, stock/mrp PERF #4.
3. **H22 done:** F49 mini scored **37/50** (tools 0→8).

## Introspect (H22 / F49 live #5)

1. **F49 third independent recovery:** POS frontend 6-file; first pass tool_turns=0; re-prompt **0→8**; F45 skipped; soul_blocked=0.
2. **Score 37/50:** mid-pack between #2 F49 (36) and #4 F49 (38); APPROVE 92 justified for pure UI if no defects — but soft i18n/`_t` + unused-import nits risk false precision (head-only file read).
3. **Cost mid:** attempt-1 ~$0.002 + attempt-2 ~$0.026 · 9 API · 56s — between #4 (~$0.017) and #2 (~$0.065).
4. **Coverage ok, depth soft:** agent found no UI tests and approved; did not stress responsive breakpoints, OWL lifecycle, or restaurant inheritance edge cases (D1/D3 ceiling).
5. **Corpus fully scored:** all 5 eval PRs have best rows; next ROI is **H20** severity or **6th** upstream PR.

## Introspect (H24 / F49 live #6)

1. **F49 fourth recovery, weakest depth:** 14-file street_split; first pass tool_turns=0; re-prompt **0→1** (vs #2 23 / #4 9 / #5 8). F45 skipped; F50 correctly no-op (`tests:yes`).
2. **Shallow tools = D8 hole:** one assistant turn with 4× parallel `head -80` — `misc.py` header only, **never** reads `street_split` ~L1925; claims in "What I checked" overstate workspace use (diff still in prompt).
3. **Score 34/50:** lowest F49 row; APPROVE 95 + soft regex-maintainability nits; cheap (~$0.005 · 2 API · 32s hermes) but quality-capped by tool depth.
4. **ROI signal:** raise H18/H26 from pure "first-pass tools" to **depth-after-reprompt** (rg/sed around diff hunks, not head).
5. **Ops:** orchestrator cancelled mid publish_local; hermes+trace+review complete; pack-run-for-ui re-run offline OK.

## Introspect (F51 / H26 tool depth)

1. **Root cause of #6 shallow recovery:** F49 only required *some* tool use; mini satisfied with parallel `head -80` and never hit the changed regex region.
2. **Minimal fix (prompt control-plane, no second hermes loop):** F49 `build_reprompt_suffix` now includes **Tool depth (H26 / F51)** — forbid head-only large files; prefer unified diff + `rg`/line-range on changed symbols. Same guidance in `agent/review-prompt.md` Workspace and one SOUL Scope bullet.
3. **Idempotency:** re-prompt marker relaxed to `## Soft re-prompt (Torii H15` so F49+F51 title does not double-append.
4. **Live-verified on #6 (H27):** see below.
5. **Was next P0:** H27 — **done**.

## Introspect (H27 / F51 live #6)

1. **F51 depth lift confirmed:** same 14-file PR; re-prompt tool_turns **0→17** (H24 was **0→1**). F45 skipped; F50 no-op; APPROVE 95; soul_blocked=0.
2. **Hunk-aware tools worked:** agent used `rg -w 'def street_split'` then `sed -n 1940,1980p odoo/tools/misc.py` (read full function + ADDRESS_REGEXES tail), plus `sed` on `res_partner` compute/inverse and test ranges — **not** misc.py header-only.
3. **Score 34→39/50:** D8 2→4, D2/D3/D5/D7/D10 up; D6 5→3 (attempt-2 ~$0.034 · 18 API · 80s vs H24 ~$0.005 · 2 API). Findings still soft (docstring) — no multi-lens security/perf pass.
4. **Residual waste:** several failed/awkward `rg --json` flag combos before simple `-w` hit; product ROI next is multi-lens structured findings or codebase packs, not more tool gates.
5. **Next P0 product:** H25 7th corpus PR **or** multi-lens review mode (PRODUCT_FEATURE) for D10 depth gap.
