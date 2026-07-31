# Torii pack templates (F10)

| File | Use |
|------|-----|
| `torii-pr-review-caller.yml` | Thin hub-managed workflow for target repos (`install-torii.sh --caller`) |

Default install (without `--caller`) still copies the full pack (`agent/`, runtime `scripts/`, and a thin caller that points at the *target* repo for scripts).

## Memory (F28)

Pack install seeds **`.torii/MEMORY.md`** on the target. After each review Torii commits a slim run pack under `.torii/runs/{trace_id}/` on the target default branch (`contents: write`). Hub memory is optional (`TORII_MEMORY_MODE=both|hub` or `TORII_HUB_PUBLISH=1`). Fat traces remain Actions artifacts only.

**F30:** job summary includes **Memory health** (preload source + `LOCAL_PUBLISH=`). Failed default-branch push emits `::warning::` (branch protection / token) — review still posts; durable memory may be stale.

## Caller pin tip (F10)

`torii-pr-review-caller.yml` uses `…/torii-review-reusable.yml@main` for free upgrades. For production fleets, **pin `uses:` to a commit SHA** so a broken hub `main` does not break every target at once.
