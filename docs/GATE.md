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

## Gate certificate (merge-authority evidence)

Every open/close is a **deterministic certificate** — reason codes + path evidence + optional critic demote — not a chat transcript. Buyers answer *"why did the gate close?"* without reading the agent loop.

```bash
python3 scripts/gate_certificate.py emit --review .torii-out/review-1.md --write .torii-out
python3 scripts/torii.py certificate -- fixture
python3 scripts/torii.py certificate -- report
```

Artifacts: `gate-certificate.json` / `.md` · scorecard: [`benchmarks/gate-certificate.md`](benchmarks/gate-certificate.md).

**Soft wire (every run):** `save-trace.sh` emits the certificate into `.torii-out/` + the per-run trace dir (disable with `TORII_GATE_CERTIFICATE=0`). The reusable workflow attaches `--certificate` when posting `torii/gate`. Ops dashboard shows the **last gate certificate** from the dogfood vault (`python3 scripts/torii.py ops -- report`).

## Entry points
```bash
./scripts/run-torii-gate.sh          # product entry (security forced)
./scripts/run-torii-review.sh        # full orchestrator
python3 scripts/torii_gate_status.py .torii-out/review-1.md --json --strict
python3 scripts/gate_certificate.py emit --review .torii-out/review-1.md --write .torii-out
```

## CI wiring
Reusable workflow posts **two** commit statuses after a matched run (when `TORII_COMMIT_STATUS` is not `0`):

| Context | Source | Merge signal |
|---------|--------|--------------|
| `torii/review` | `report-verdict.sh` / parse-verdict (F22) | Verdict-aware reaction + status |
| `torii/gate` | `torii_gate_status.py` post-step | Security-aware open/closed |

Required checks for a hard merge gate should use **`torii/gate`**. Optional hard job fail: repo var `TORII_GATE_STRICT=1`.

**Commercial golden path (install → required check → dogfood → FP/TP):** [`GOLDEN-PATH.md`](GOLDEN-PATH.md) · metrics [`benchmarks/golden-path-metrics.md`](benchmarks/golden-path-metrics.md).

**Own-repo quieter-over-time:** require **`torii/gate`**, then measure path evidence / tool use / weak APPROVE over dogfood → [`QUIETER.md`](QUIETER.md) · `python3 scripts/torii.py quieter -- report`.

**Reliability / ops:** fail-closed defaults · cost/PR stub · smoke CI → [`ops/RELIABILITY.md`](ops/RELIABILITY.md) · [`ops/DASHBOARD.md`](ops/DASHBOARD.md).

```bash
python3 scripts/golden_path_metrics.py fixture
python3 scripts/golden_path_metrics.py report
python3 scripts/ops_dashboard.py report --smoke
./scripts/smoke-torii-gate.sh   # also .github/workflows/smoke-offline.yml
```

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

## Workflows-as-code (F79)

Declarative pipeline: [`docs/workflows/torii-gate.workflow.yaml`](workflows/torii-gate.workflow.yaml).

```bash
python3 scripts/workflow_as_code.py validate
python3 scripts/workflow_as_code.py plan
python3 scripts/workflow_as_code.py install-guide   # capability matrix
python3 scripts/workflow_as_code.py status          # readiness L0–L3
```

Install guide (generated): [`docs/workflows/INSTALL-GUIDE.md`](workflows/INSTALL-GUIDE.md).

## Eval traces (F83)

Paper-ready aggregate:

```bash
python3 scripts/eval_trace_report.py report
# → docs/benchmarks/traces/EVAL-REPORT.md + eval-report.json
```

Pack installs now ship `agent/skills/active/` (evolved skills) and `agent/tools/`.

