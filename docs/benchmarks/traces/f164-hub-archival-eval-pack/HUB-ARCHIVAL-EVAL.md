# Hub-archival compound loop — paper EVAL pack (F155–F163 / F164)

_Generated: `2026-08-01T11:00:57Z` · brand bit: `hub_archival_loop_ok` · model: deepseek/deepseek-v4-pro_

## Claim

Torii measures hub-prefer archival skills end-to-end: inject → tool util → critic demote →
budgeted re-prompt → fitness → multi-tenant hub pressure → prompt inject. Product readiness is
one flag (`hub_archival_loop_ok`) on doctor/scorecard — not fragmented script wires.

## Live proofs (Modal pytorch, POST_COMMENT=0)

| Feature | Trace dir | util_rate | recall | recovery_n | PR | Modal | stream |
|---------|-----------|----------:|-------:|-----------:|---:|-------|:------:|
| F155 | `f155-hub-archival-recovery-util` | 0.5 | 1.0 | — | 191831 | BIT3_OK | True |
| F156 | `f156-hub-archival-util-critic` | — | 1.0 | — | 191831 | BIT3_OK | True |
| F157 | `f157-hub-archival-util-reprompt` | — | 1.0 | — | 191829 | BIT3_OK | True |
| F158 | `f158-hub-archival-fitness` | — | 1.0 | — | 191831 | BIT3_OK | True |
| F159 | `f159-reprompt-adaptive-dual` | — | 1.0 | — | 191829 | BIT3_OK | True |
| F160 | `f160-skill-router-synth` | 1.0 | 1.0 | 3 | 191831 | BIT3_OK | True |
| F161 | `f161-hub-archival-hub-pressure` | 1.0 | 1.0 | 3 | 191829 | BIT3_OK | True |
| F162 | `f162-hub-archival-hub-inject` | 1.0 | 1.0 | 3 | 191831 | BIT3_OK | True |
| F163 | `f163-hub-archival-loop-product` | 1.0 | 1.0 | 3 | 191829 | BIT3_OK | True |

## Aggregate

- fires packaged: **9** (F155–F163)
- modal BIT3_OK: **9**
- util_rate=1.0 runs: **4**
- F163 doctor hub_archival_loop_ok: **True**

## Product surfaces (F164)

- `PRODUCT.md` Mental model D
- `docs/brand/TORII.md` one-liners
- `docs/brand/landing.html` hub-archival pipeline
- `docs/brand/scorecard-metrics.md` measured rows via `torii.py scorecard`

## Privacy

Traces redacted; federation themes only (no paths/snippets/home). No secrets in vault.
