# DEV — engineering knowledge

> How this part of the system is built.

## Design decisions

- **Run Console** loads a single `run-bundle.json` (F31 pack) — operators never need raw Hermes logs for first triage.
- **Ops signals (F40+)** surface gates as chips + Overview rows: path-skip, timeout, over-budget, diff-truncated, max-turns (F41), model-tier (F42).
- **F42 model tier** chips (`model-cheap` / `model-full`) come from pack `signals` filled by `model-tier.env`; Overview shows mode/tier/reason + effective model id.
- **F43 preflight cost** chips (`preflight-cheap` / `preflight-refuse`) come from `preflight-cost.env` via pack signals — refuse means no Hermes spend; forced-cheap means estimate exceeded budget on the premium model.
- Agent loop panel (F41) is separate from cost model tier: turns thrash vs which OpenRouter model was selected.
- Browser is not a kitchen: **Run** tab copies `trigger-review.sh` / Modal commands; review work stays in GHA/Modal.

- **F49 adds a chip pair** to the pack signals, not a single flag: `tool-reprompt` (a soft re-prompt was attempted) and `tool-reprompt-ok` (the second pass actually produced tool turns). Both are filled from `tool-turns-reprompt.env`, so the console can distinguish "we retried" from "the retry worked" without opening the raw logs — a run showing `tool-reprompt` without `tool-reprompt-ok` is the H18 escalation signal.

## Pitfalls

- Fixture re-pack (`npm run pack-fixture`) must stay green after pack-run signal shape changes or Overview types drift.
- Empty `signals.flags` means either a clean paid run *or* tier mode was `off` — check `signals.model_tier_mode` before assuming auto-tier ran.
