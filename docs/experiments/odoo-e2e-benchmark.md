# Odoo e2e qualitative benchmark

Rubric dims (1–5 each; one-line evidence). Recursive: dim ≤2 gets sub-dims.

| Dim | Name |
|-----|------|
| D1 | Signal quality — true issues vs noise |
| D2 | Coverage — important risk areas hit |
| D3 | Actionability — fixable, concrete |
| D4 | Trust/citations — grounded in diff |
| D5 | Inline precision — line-level correctness |
| D6 | Cost efficiency — model/turns/budget |
| D7 | Latency/ops — finished, traces usable |
| D8 | Memory/context use — repo/memory leveraged |
| D9 | Severity ranking — priorities sensible |
| D10 | vs PR-Agent/Hermes-style expectations |

## Per-PR scores

| PR | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 | Total/50 | Top gap |
|----|----|----|----|----|----|----|----|----|----|-----|----------|---------|
| #1 turnstile (GHA) | 4 | 3 | 4 | 4 | 3 | 4 | 4 | 2 | 4 | 3 | **35** | D8 memory thin |
| #2 web fields (GHA) | 5 | 4 | 5 | 4 | 3 | 4 | 4 | 2 | 5 | 4 | **40** | D8; D5 soft lines |
| #2 web fields (F44 mini local) | 2 | 3 | 2 | 3 | 2 | 5 | 3 | 1 | 2 | 2 | **25** | D1/D3/D8 no tools + SOUL block |
| #2 web fields (F45 gate on F44) | 3 | 3 | 2 | 4 | 2 | 5 | 4 | 1 | 3 | 3 | **30** | Still no tools; no longer false APPROVE |
| #2 web fields (H16 mini post-F47) | 2 | 3 | 2 | 4 | 2 | 5 | 4 | 2 | 3 | 3 | **30** | -z ok; tool_turns=0 model choice; F45 gate |
| #2 web fields (F49 mini re-prompt) | 3 | 4 | 4 | 4 | 3 | 3 | 5 | 3 | 3 | 4 | **36** | tools 0→23 recovered; still soft vs GHA gap |
| #2 web fields (F50 offline on F49) | 4 | 4 | 4 | 5 | 3 | 4 | 5 | 3 | 5 | 5 | **42** | F50 APPROVE→REQUEST CHANGES; score 95→69; match GHA test-gap severity |
| #3 xml scrub (local mini+showcase) | 4 | 4 | 4 | 4 | 3 | 4 | 5 | 3 | 4 | 4 | **39** | D5 inline |
| #4 stock/mrp PERF (mini post-F48) | 2 | 3 | 2 | 4 | 2 | 5 | 5 | 2 | 3 | 3 | **31** | tool_turns=0; multi-module needs tools; F49 not re-run |
| #4 stock/mrp PERF (F49 mini re-prompt) | 3 | 4 | 4 | 4 | 3 | 4 | 5 | 3 | 4 | 4 | **38** | tools 0→9; soft comment nits only; no deep PERF hazards |
| #5 POS ticket (F49 mini re-prompt) | 3 | 4 | 3 | 4 | 3 | 4 | 5 | 3 | 4 | 4 | **37** | tools 0→8; soft i18n/import nits; no deep layout/responsive hazards |
| #5 POS ticket (F50 offline on F49) | 3 | 4 | 4 | 5 | 3 | 4 | 5 | 3 | 5 | 4 | **40** | F50 tests:no under APPROVE → REQUEST CHANGES; score 92→69 |
| #6 street_split (F49 mini re-prompt) | 3 | 3 | 3 | 4 | 3 | 5 | 4 | 2 | 4 | 3 | **34** | tools 0→1 only; head-only misses street_split region; soft regex nits |
| #6 street_split (F51 mini H27) | 3 | 4 | 4 | 4 | 4 | 3 | 5 | 4 | 4 | 4 | **39** | tools 0→17; rg+sed on street_split L1950; soft doc only; multi-lens still thin |

### Evidence (one line)

- **#1:** Blocking null-guard on successCb is plausible race; nits on style. Memory seed only.
- **#2 GHA:** Correct high-signal block: format alias untested while getFieldsSpec tests present.
- **#2 F44 mini:** APPROVE despite same gap; medium findings are speculative (“other field types”); raw was prompt-polluted until F44.
- **#2 F45 gate:** Same body post-processed — APPROVE→COMMENT + F45 banner + score 55; honesty/trust up, findings unchanged.
- **#2 H16 mini:** F47 confirmed — `hermes -z` (no argv reject, no chat fallback); 1 API call · ~$0.003 · 12s; still `tool_turns=0` (model single-shot); F45→COMMENT/55; F46 preflight clean; **false** runtime `soul_blocked` from stale agent.log → **F48**.
- **#2 F49 mini:** Soft re-prompt recovered `tool_turns` **0→23** (session `20260731_221752_851ba1`); F45 gate skipped (`tools_used`); APPROVE 95 · ~$0.063 · 24 API · 95s; soft float `format:false` test ask (not GHA-level REQUEST CHANGES on missing alias tests); chip `tool-reprompt-ok`; soul_blocked=0.
- **#2 F50 offline:** `severity_calibration.py apply` on F49 body — match=`missing_tests:suggestions` (“enhance test coverage”); APPROVE→**REQUEST CHANGES**, score **95→69**, F50 banner; D9 3→5; total **42/50** (was 36). Aligns with GHA blocking missing alias tests.
- **#3:** Approve justified; tests cover str/bytes/lxml; showcase loop usable.
- **#4 mini:** Port of odoo#279776 (7 files stock/mrp/purchase_mrp); `-z` ok; F48 `soul_blocked=0`; tool_turns=0 → F45 COMMENT/55; soft rename nit only; ~$0.002 · 16s.
- **#4 F49 mini:** Soft re-prompt recovered `tool_turns` **0→9** (sessions `20260731_222340_fb13a3` → `20260731_222355_b47e5a`); F45 skipped; APPROVE 95 · attempt-2 ~$0.014 · 10 API · total ~58s (attempt-1 ~$0.003); read mrp orderpoint/rule + tests; cache-comment suggestion only; chip `tool-reprompt-ok`; soul_blocked=0; score **38/50** (was 31).
- **#5 F49 mini:** Soft re-prompt recovered `tool_turns` **0→8** (sessions `20260731_223146_62f430` → `20260731_223158_96a569`); F45 skipped (`tools_used`); APPROVE 92 · attempt-2 ~$0.026 · 9 API · total ~56s (attempt-1 ~$0.002); read ticket_screen js/xml/scss + pos_restaurant; noted no UI tests; soft i18n/`_t` + unused-import nits (partial-read risk); chip `tool-reprompt-ok`; soul_blocked=0; score **37/50**.
- **#5 F50 offline:** match=`tests_no_line` (Relevant tests: no) under APPROVE 92 → **REQUEST CHANGES** + score 69; #4 F49 clean (no gap signal, stays APPROVE).
- **#6 port (H23):** odoo#279777 → Mr-Ashish/odoo#6; 14 files tools/misc street_split + base_address_extended tests + l10n_dk_nemhandel/oioubl fixtures; apply clean 3way onto 19.0.
- **#6 F49 mini (H24):** recovered tool_turns **0→1** (sessions `20260731_225136_8453c3` → `20260731_225149_76bc30`); F45 skipped; F50 no-op (`no_test_gap_signal`, tests:yes); APPROVE 95 · attempt-2 ~$0.005 · 2 API · hermes ~32s wall; soul_blocked=0; chip `tool-reprompt-ok`; **shallow tools:** one turn with 4× `head -80` (misc.py header only — street_split ~L1925 never read); soft medium regex-complexity nits; score **34/50**.
- **#6 F51 mini (H27):** F49+F51 re-prompt recovered tool_turns **0→17** (sessions `20260731_230213_7d82f2` → `20260731_230226_bba7bf`); F45 skipped; F50 no-op; APPROVE 95 · attempt-2 ~$0.034 · 18 API · total ~80s; soul_blocked=0; chip `tool-reprompt-ok`; **deep tools:** `rg -w 'def street_split'` → `sed -n 1940,1980p odoo/tools/misc.py` (read function body) + partner compute/inverse + test_street_fields ranges; soft docstring suggestion only; score **39/50** (+5 vs H24). D8 2→4; D6 5→3 (cost ↑ with depth).

### #6 F51 sub-dims (H27; D6=3, D8=4)

| Sub | Score | Note |
|-----|------:|------|
| D2a symbol coverage | 4 | street_split + res_partner compute/inverse + tests touched |
| D5a line-range reads | 4 | `sed -n 1940,1980p` on misc.py (not head-80 header) |
| D6a attempt cost | 3 | ~$0.034 · 18 API vs H24 ~$0.005 · 2 API |
| D8b tool/workspace use | 4 | 17 turns; rg locate + sed hunk; some wasted rg json flags |
| D10a multi-lens | 3 | still single-pass; no security/perf/API lenses |

### #2 F44 sub-dims (D1=2, D3=2, D8=1)

| Sub | Score | Note |
|-----|------:|------|
| D1a true positives | 1 | Missed missing alias tests (known from GHA) |
| D1b false positives / noise | 2 | console.warn + cross-type alias expansion |
| D3a concrete fix steps | 2 | Diff suggestions rewrite same code |
| D3b test asks | 1 | Claimed coverage complete incorrectly |
| D8a SOUL/memory load | 1 | SOUL blocked prompt_injection |
| D8b tool/workspace use | 1 | tool_turns=0 |

### #2 F45 sub-dims (post-gate; D1=3, D8=1)

| Sub | Score | Note |
|-----|------:|------|
| D1a true positives | 1 | Still missed alias tests (gate does not invent findings) |
| D1b false approve risk | 4 | Fail-closed: no merge-green without tools |
| D4 trust | 4 | Banner + COMMENT state the incomplete loop |
| D8b tool/workspace use | 1 | Unchanged — still 0 tool turns |

### #2 H16 sub-dims (post-F47 live mini; D1=2, D8=2)

| Sub | Score | Note |
|-----|------:|------|
| D1a true positives | 1 | Still missed missing `format:false` alias tests (GHA gap) |
| D1b false positives / noise | 3 | Mostly empty findings; one soft rename nit |
| D7a hermes -z path | 5 | No `invalid choice`; no chat fallback; no `hermes-cli-argv.env` |
| D8a SOUL/memory load | 3 | Preflight clean; pin `scan_for_threats` empty; runtime FP fixed in F48 |
| D8b tool/workspace use | 1 | `tool_turns=0` — model chose text stop (not CLI failure) |

### #2 F49 sub-dims (D1=3, D6=3, D8=3)

| Sub | Score | Note |
|-----|------:|------|
| D1a true positives | 3 | Soft float `format:false` test gap; still not GHA blocking severity |
| D1b false positives / noise | 4 | Less empty-approve than attempt-1; comment-on-alias nit ok |
| D6a attempt cost | 3 | ~$0.063 + 24 calls vs attempt-1 ~$0.002 (2× hermes -z) |
| D7a reprompt path | 5 | recovered=1; F45 skipped; soul_blocked=0; 95s |
| D8b tool/workspace use | 4 | 23 tool turns; terminal `rg` + file reads across PR paths |

### #4 F49 sub-dims (D1=3, D6=4, D8=3)

| Sub | Score | Note |
|-----|------:|------|
| D1a true positives | 3 | No invented defects on PERF+tests; soft multi-company cache note only |
| D1b false positives / noise | 4 | Empty findings table OK for low-risk PERF; no rename-nit spam |
| D2a multi-module coverage | 4 | mrp orderpoint/rule + purchase_mrp tests checked after tools |
| D6a attempt cost | 4 | attempt-2 ~$0.014 · 10 API (cheaper recovery than #2 F49) |
| D7a reprompt path | 5 | recovered 0→9; F45 skipped; soul_blocked=0; ~58s wall |
| D8b tool/workspace use | 4 | 9 tool turns on 7-file stock/mrp/purchase_mrp |
| D9 severity vs GHA | 3 | APPROVE 95 vs GHA REQUEST CHANGES on missing alias tests |

### #4 mini sub-dims (D1=2, D8=2)

| Sub | Score | Note |
|-----|------:|------|
| D1a true positives | 1 | No cache/correctness risks called out on multi-module PERF |
| D1b noise | 3 | Soft rename nit only after F45 |
| D7a ops (F48) | 5 | `soul_blocked=0`; `-z` clean; no argv env |
| D8b tool/workspace use | 1 | tool_turns=0 on 7-file PR |

## Rollup (best run per PR for corpus avg)

| PR | Best total | Primary gap |
|----|------------|-------------|
| #1 | 35 | Memory/context |
| #2 | 40 (GHA); cheap F49 **36** | GHA still best signal; mini recovered tools |
| #3 | 39 | Inline precision |
| #4 | 31 (mini pre-F49) | Needs F49 re-run; tool_turns=0 legacy |

**Corpus average (best-per-PR): 36.3 / 50** (unchanged — #2 best still GHA 40)  
**Cheap-path after F49 (#2):** attempt-1 still 0 tools → soft re-prompt → **23 tools**, total **36/50** (was 30 H16). D1 still lags GHA severity ranking.

### F49 live verify (done on #2)

- Artifacts: `.torii-out-e2e-pr2-f49/` · run `pr2-runlocal-a1` · `tool-turns-reprompt.env` recovered=1 (0→23).
- **#4 F49 re-run still pending** for multi-module PERF confirmation.
- H18 demoted from P0 (recovery works); optional for first-pass tools / cost.

## Comparison notes (D10)

- PR-Agent-style: stronger structured findings tables + severity; Torii GHA run competitive; chat-fallback path is not.
- Hermes-style: agentic tool loop is the product differentiator — F49 proves recovery works on mini (`tool_turns` 0→23); attempt-1 alone still 0 tools.
- F45: control-plane fail-closed mirrors “don’t ship green without tools” — PR-Agent never claimed agentic; we must not green-light when we aren’t. F49 recovered → gate skipped.

### F46 note (SOUL load)

Product `agent/SOUL.md` no longer trips Hermes `prompt_injection` (verified with
pin `scan_for_threats`). H16 preflight clean. Historical F44 SOUL-block row kept.

### F47 note (hermes -z reliability)

Root cause of F44 zero-tool path: bogus CLI `--max-turns` → `-z` rc=2 → `chat -q`.
**H16 live verify:** `-z` path works (stderr header `hermes -z`, no argv env). Residual
`tool_turns=0` is **model behaviour** (single text response), not CLI failure.

### F48 note (SOUL detect false positive)

H16 ops noise: `soul_blocked=1` while this-invocation `hermes-run.log` had no block line.
Root cause: detect scanned full `HERMES_HOME` agent.log history (prior session still had
`Context file SOUL.md blocked`). F48: pass `HERMES_LOG_OFFSET` into capture; package only
the this-run log slice; detect only invocation-scoped logs.

### Corpus #4 note

Sourced upstream [odoo/odoo#279776](https://github.com/odoo/odoo/pull/279776) → [Mr-Ashish/odoo#4](https://github.com/Mr-Ashish/odoo/pull/4).
First multi-module backend PERF eval PR. Confirms H16 cheap-path residual on a second PR.

_Last updated: 2026-07-31 F49 live #2_

### #6 F49 sub-dims (D2=3, D8=2)

| Sub | Score | Note |
|-----|------:|------|
| D2a multi-file coverage | 3 | 14 files claimed; only 4 heads sampled |
| D8b tool/workspace use | 2 | tool_turns 0→1; head -80 misses street_split ~L1925 |
| D6a attempt cost | 5 | ~$0.005 · 2 API · 32s hermes (cheapest F49 recovery) |
| D7a reprompt path | 5 | recovered=1; F45 skipped; F50 no-op; soul_blocked=0 |
| D9 severity | 4 | APPROVE ok with tests updated; F50 correctly idle |

