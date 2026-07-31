# Session

- **session_id:** `dogfood-torii-session`
- **source:** `file`
- **project:** `/Users/ashishmishra/Documents/experiments/pr-review-agent`
- **timestamp:** ``

## Transcript / notes

# Torii dogfood session — F51 tool depth (H26)

## Shipped
- F51: tool-depth nudge after F49 soft re-prompt (H26)
- Evidence: odoo eval #6 F49 recovered 0→1 tools but only `head -80` on large misc.py; never read street_split ~L1925; score 34/50 D8=2
- Fix: build_reprompt_suffix + review-prompt Workspace + SOUL Scope require diff hunks / rg + line-range on changed symbols; forbid head-only large-file reads
- Tests: test_tool_turns_gate tool_depth_h26; SOUL preflight clean
- SHA: d27b477 on origin/main

## Next
- H27 live mini re-score #6 under F51
- H25 source 7th complex odoo/odoo PR

## Ops
- Corpus: 6 torii-eval PRs on Mr-Ashish/odoo all scored
- No .env committed

