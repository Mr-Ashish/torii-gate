# DEV — engineering knowledge

> How this part of the system is built.

## Architecture

- `pack/` holds installable templates that are *not* live workflows in this repo: `torii-pr-review-caller.yml` is the F10 hub-managed thin caller, copied verbatim to `.github/workflows/torii-pr-review.yml` on the target by `install-torii.sh --caller`.
- It differs from this repo's own `torii-pr-review.yml` in exactly one way: `uses:` is the absolute hub ref `Mr-Ashish/torii-gate/.github/workflows/torii-review-reusable.yml@main` with literal `torii_repository`/`torii_ref` values, instead of the local `./.github/workflows/...` path with `github.repository`.
- Triggers, `permissions`, and the `torii-${{ github.repository }}-<pr>` concurrency group are duplicated in the template because a `workflow_call` job cannot own them — edits to gating must be applied to `pack/torii-pr-review-caller.yml` as well as the in-repo caller.

## Design decisions

- Pack-mode install now seeds the target's `.torii/MEMORY.md` (`seed_local_memory()` in `install-torii.sh`), copying `agent/MEMORY.seed.md` when present and falling back to an inline stub. It honours `--force` (skips an existing file otherwise) and `--dry-run`, and runs before `write_stamp "pack"`.
- `--caller` (hub-managed thin) installs **do not** seed `.torii/` because no agent/scripts are copied — the installer instead prints a tip to seed `.torii/MEMORY.md` manually on the default branch (or run pack mode once). A caller repo with no seed simply starts from `MEMORY_SOURCE=seed`.
- Regression coverage lives in `tests/test_install_torii.py`: pack install asserts both `scripts/publish-run-local.sh` and `.torii/MEMORY.md` exist.

- The install pack now ships `scripts/trigger-review.sh`, so an installed target repo can drive reviews from any host (print/local/modal) without cloning the hub. Adding a new top-level trigger script therefore requires updating the pack's copied-scripts list, not just the hub repo.
