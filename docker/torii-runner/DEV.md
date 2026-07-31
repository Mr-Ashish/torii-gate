# DEV — engineering knowledge

> How this part of the system is built.

## Design decisions

- The image's job is to satisfy a two-signal contract that CI probes, not to run Torii itself: it sets `TORII_HERMES_PREBAKED=1` and writes the resolved SHA to `/root/.hermes-pin`, and bakes `PATH=/root/.local/bin:/root/.hermes/bin`. `ensure_hermes` short-circuits when either signal is present *and* `hermes` is on PATH, so a broken/renamed marker silently falls back to a cold install instead of failing loudly.
- Base is plain `ubuntu:24.04` plus the minimum Hermes needs (`ca-certificates curl git python3 python3-venv bash build-essential`); Hermes is installed at build time with `install.sh --skip-setup --commit "${HERMES_COMMIT}" --force-commit`, i.e. the same pinned, non-interactive install path CI uses (F7).
- The pin is an `ARG HERMES_COMMIT` with a hardcoded default that must track `scripts/hermes-pin.sh` DEFAULT — `scripts/build-torii-runner-image.sh` resolves the pin via `scripts/hermes-pin.sh default` (overridable with `HERMES_COMMIT=…`) and passes it as `--build-arg`, so the Dockerfile default only matters for raw `docker build` invocations.
- Tagging is pin-derived, not semver: `ghcr.io/<owner>/torii-hermes-runner:<first-12-chars-of-pin>` plus `:latest`, which makes the image ref self-documenting about which Hermes commit is inside.
- The build script gates publication on a smoke run (`docker run --rm <tag> hermes --version`) before any push, and only pushes when `PUSH=1`; the GHCR workflow (`.github/workflows/build-torii-runner.yml`) rebuilds on pin/Dockerfile changes.
