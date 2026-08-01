# Gate certificate pattern — merge-authority evidence (tools-as-code)

**Date:** 2026-08-01  
**Fire:** GATE_CERT (post commercial queue 1–6)

## Sources

1. Loop Engineering: verifiers emit checklists, not prose; default REJECT until evidence.
2. SLSA / supply-chain attestations: machine-readable reasons for pass/fail gates.
3. Torii PRODUCT success metric: *PRs blocked with path-evidenced findings* — was not a first-class artifact.
4. Buyer narrative: hide F-stack; answer *"why did the gate close?"* without opening agent logs.

## Pattern

| Idea | Port |
|------|------|
| Deterministic reason codes | `verdict_request_changes`, `low_path_evidence`, `critic_demoted_maker`, … |
| Path evidence reuse | `trajectory_fitness.score_path_evidence` |
| Optional critic attach | second-agent critic JSON demote reasons → codes |
| Content hash | sha256-16 of stable body for audit |
| Product surface | `gate_certificate.py` + `torii.py certificate` + GATE.md |

## Decide / copy / skip

- **Copy:** attestation-style certificate next to merge status (not a new compound loop).
- **Skip:** more F185+ GEPA/reprompt compound layers (worsens simplicity #12).
- **Decide:** certificate never blocks alone; `torii/gate` decision stays source of truth; cert explains it.

## Success metric

- Hermetic fixture 11/11; good → CLOSED + path≥0.45; weak → OPEN + low_path + critic codes.
- Live Modal BIT3 still green; cert emit offline from review fixture.
