# Torii Gate — product contract (v1)

## Trigger
- PR comment: `@torii review this pr` or `@torii review`
- Manual: Actions → **Torii Gate** → PR number

## Default behavior
| Setting | Value |
|---------|-------|
| Lens pack | `security` |
| Memory path | `.torii/` |
| Labels | on (`torii/*` prefix) |
| Commit status | `torii/gate` (via `torii_gate_status.py`) |

## Gate policy
| Verdict / security | Gate |
|--------------------|------|
| APPROVE + Security audit No | **Open** (success) |
| REQUEST CHANGES | **Closed** (failure) |
| Security audit non-empty concern | **Closed** |
| COMMENT / advisory | Open (non-blocking) unless `--strict` security |

## Entry points
```bash
./scripts/run-torii-gate.sh          # product entry (security forced)
./scripts/run-torii-review.sh        # full orchestrator
python3 scripts/torii_gate_status.py .torii-out/review-1.md --json --strict
```

## Roadmap hooks
- **Trust:** ingest SARIF before agent; only validated findings block
- **Plane:** policy JSON for coding agents (tool allowlists, spend)
