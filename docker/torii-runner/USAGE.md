# USAGE — operational knowledge

> How to work with this part of the system.

## Setup

- Order of operations to adopt the prebaked runner: (1) publish the image (`PUSH=1 ./scripts/build-torii-runner-image.sh` or the **Build Torii Hermes runner** workflow), (2) make the GHCR package readable by Actions — public package, or explicitly grant the consuming repo access, (3) set repo variable `TORII_RUNNER_IMAGE` to the pin-tagged ref (e.g. `ghcr.io/mr-ashish/torii-hermes-runner:53559aaf86b8`), (4) re-trigger `@torii review`.
- The workflow resolves the container as `${{ vars.TORII_RUNNER_IMAGE != '' && vars.TORII_RUNNER_IMAGE || null }}`, so leaving the variable unset (or empty) is the supported default path: host `ubuntu-latest` + pin-keyed Hermes install cache. There is no separate on/off flag.
- Verify an image locally before wiring it into CI: `docker run --rm ghcr.io/mr-ashish/torii-hermes-runner:latest hermes --version`.

## Troubleshooting

- A stale `TORII_RUNNER_IMAGE` pin is invisible: the prebaked short-circuit returns before any pin comparison, so a container built from an older `HERMES_COMMIT` will run happily against a newer `scripts/hermes-pin.sh` default. Compare the image tag's 12-char pin against `scripts/hermes-pin.sh default` when Hermes behaviour differs between the container path and the host path.
- Self-hosted runners can opt into the same fast path without the image by placing `hermes` on PATH plus a `/root/.hermes-pin` (or `$HOME/.hermes-pin`) marker file.
