# Torii pack templates (F10)

| File | Use |
|------|-----|
| `torii-pr-review-caller.yml` | Thin hub-managed workflow for target repos (`install-torii.sh --caller`) |

Default install (without `--caller`) still copies the full pack (`agent/`, runtime `scripts/`, and a thin caller that points at the *target* repo for scripts).

## Memory (F28)

Pack install seeds **`.torii/MEMORY.md`** on the target. After each review Torii commits a slim run pack under `.torii/runs/{trace_id}/` on the target default branch (`contents: write`). Hub memory is optional (`TORII_MEMORY_MODE=both|hub` or `TORII_HUB_PUBLISH=1`). Fat traces remain Actions artifacts only.

**F30:** job summary includes **Memory health** (preload source + `LOCAL_PUBLISH=`). Failed default-branch push emits `::warning::` (branch protection / token) — review still posts; durable memory may be stale.

## Merge gate

After each review the workflow posts commit status **`torii/gate`** (security-aware open/closed via `torii_gate_status.py`). Prefer that context as the required branch-protection check. F22 still posts `torii/review` for the classic verdict signal.

Pack mode also installs `scripts/run-torii-gate.sh`, `scripts/torii_gate_status.py`, and `scripts/smoke-torii-gate.sh`.

## Caller pin tip (F10)

`torii-pr-review-caller.yml` uses `…/torii-review-reusable.yml@main` for free upgrades. For production fleets, **pin `uses:` to a commit SHA** so a broken hub `main` does not break every target at once.

## Workflows-as-code (F79)

After pack install, from the target (or hub) checkout:

```bash
python3 scripts/workflow_as_code.py install-guide
python3 scripts/workflow_as_code.py validate
```

See hub `docs/workflows/torii-gate.workflow.yaml` for the declarative stage graph and capability matrix.
