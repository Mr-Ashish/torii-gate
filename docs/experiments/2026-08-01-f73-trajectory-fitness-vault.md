# F73: Trajectory fitness + paper-ready eval-trace vault

## Summary
Deterministic multi-dimensional fitness scorer for agent-loop procedure quality
(Hermes self-evolution style, no LLM judge) plus versioned slim vault under
`docs/benchmarks/traces/` with INDEX for paper/eval.

## Commands
```bash
python3 scripts/trajectory_fitness.py score REVIEW.md [--loop agent-loop.json] [--chain chain-revalidate.json]
python3 scripts/trajectory_fitness.py inject prompt.md
python3 scripts/trajectory_fitness.py archive --out-dir OUT --review REVIEW.md --label e2e --repo R --pr N
python3 scripts/trajectory_fitness.py fixture [--archive]
python3 scripts/trajectory_fitness.py pack --out-dir OUT --promote
```

## Toggles
- `TORII_TRAJECTORY_FITNESS` (default on) — rubric inject + post-run score
- `TORII_TRACE_VAULT` (default on) — archive to docs/benchmarks/traces/

## Wire points
- `assemble-context.sh` — inject rubric marker `<!-- torii-f73-trajectory-fitness -->`
- `run-torii-review.sh` — post-review `pack --promote`
- `save-trace.sh` — soft vault archive

## Live e2e
- Repo: pytorch/pytorch PR #191813
- Model: deepseek/deepseek-v4-pro
- POST_COMMENT=0
- Fitness: composite=0.8694 level=L3 path_evidence=1.0 procedure=0.9375 tool_use=0.65
- Vault: `docs/benchmarks/traces/20260801-0016-pytorch-pytorch-PR191813-pytorch-pr191813-172d21b`

## Offline
- fixture good composite≥0.55; weak lower; delta≥0.15
- pytest: test_trajectory_fitness (6) + full suite
