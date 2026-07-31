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

## CI wiring
Reusable workflow posts **two** commit statuses after a matched run (when `TORII_COMMIT_STATUS` is not `0`):

| Context | Source | Merge signal |
|---------|--------|--------------|
| `torii/review` | `report-verdict.sh` / parse-verdict (F22) | Verdict-aware reaction + status |
| `torii/gate` | `torii_gate_status.py` post-step | Security-aware open/closed |

Required checks for a hard merge gate should use **`torii/gate`**. Optional hard job fail: repo var `TORII_GATE_STRICT=1`.

## Dogfood
Intentional insecure sample: `demo/insecure/` (SQLi / pickle / shell / secret leak). See `demo/insecure/README.md`.

```bash
./scripts/smoke-torii-gate.sh   # offline: pack default + gate map + workflow wire + fixture
# Live: PR touching demo/insecure/app.py → @torii review this pr
```

Benchmark stub (Juice Shop eval plan): [docs/benchmarks/juice-shop-harness.md](benchmarks/juice-shop-harness.md).

## Roadmap hooks
- **Trust:** ingest SARIF before agent; only validated findings block
- **Plane:** policy JSON for coding agents (tool allowlists, spend)
