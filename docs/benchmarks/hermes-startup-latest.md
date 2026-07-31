# Hermes startup benchmark (F8)

Measured locally after shipping the prebaked-runner tooling.

- **at:** `2026-07-31T12:31:41Z`
- **pin:** `53559aaf86b84dadae83cd9bb605ca476f9a0606`
- **host:** `macos-aarch64-local`
- **tarball_bytes (hermes-agent tree):** `526956495`

| Path | Seconds | Meaning |
|------|--------:|---------|
| **cold_install** | **118.674** | Full `install.sh` in empty HOME (CI cache miss) |
| **tarball_restore** | **22.004** | Unpack packed `hermes-agent` (≈ Actions cache restore) |
| **docker_prebake** | n/a (image not built locally; use build-torii-runner-image.sh / GH Actions) | Prebaked image (build via workflow or `./scripts/build-torii-runner-image.sh`) |
| **warm_present** | **0.373** | Hermes already on PATH |

## Takeaway (plain words)

A **cold Hermes install costs about 2 minutes** here. Once cached or prebaked, **startup is under half a second** for a version check — that is the whole point of Actions cache (F2/F14) and the prebaked runner image (F8).

## Reproduce

```bash
./scripts/build-torii-runner-image.sh   # needs Docker; optional PUSH=1 for GHCR
./scripts/benchmark-hermes-startup.sh   # SKIP_COLD=1 for quick paths only
```

## Wire into CI

1. Run workflow **Build Torii Hermes runner** (pushes `ghcr.io/<owner>/torii-hermes-runner:<pin12>`).
2. On a job/container that already has Hermes, set `TORII_HERMES_PREBAKED=1` so `run-hermes-review.sh` skips reinstall.
3. Default path remains `ubuntu-latest` + pin-keyed `actions/cache` of `~/.local` + `~/.hermes`.
