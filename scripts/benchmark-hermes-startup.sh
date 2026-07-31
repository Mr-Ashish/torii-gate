#!/usr/bin/env bash
# F8: Benchmark Hermes startup paths used by Torii CI.
#
# Measures wall-clock (seconds) for:
#   cold_install   — isolated HOME, full install.sh at pin
#   warm_present   — hermes already on PATH
#   tarball_restore— unpack a pre-packed ~/.local+~/.hermes tree (Actions-cache proxy)
#   docker_prebake — docker run prebaked image hermes --version (if image exists)
#
# Usage:
#   ./scripts/benchmark-hermes-startup.sh
#   SKIP_COLD=1 ./scripts/benchmark-hermes-startup.sh
#   BENCH_OUT=docs/benchmarks/hermes-startup.json ./scripts/benchmark-hermes-startup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIN_HELPER="$ROOT/scripts/hermes-pin.sh"
PIN="$(TORII_HERMES_COMMIT="${TORII_HERMES_COMMIT:-}" "$PIN_HELPER" resolve | tr -d '\n')"
if [[ -z "$PIN" ]]; then
  PIN="$("$PIN_HELPER" default | tr -d '\n')"
fi
SHORT="${PIN:0:12}"
IMAGE_BASE="${TORII_RUNNER_IMAGE_BASE:-ghcr.io/mr-ashish/torii-hermes-runner}"
IMAGE="${TORII_RUNNER_IMAGE:-${IMAGE_BASE}:${SHORT}}"
BENCH_OUT="${BENCH_OUT:-$ROOT/docs/benchmarks/hermes-startup-latest.json}"
SKIP_COLD="${SKIP_COLD:-0}"

log() { echo "$*" >&2; }
now() { python3 -c 'import time; print(time.time())'; }
elapsed() { python3 -c "import time; print(f'{time.time() - float(\"$1\"):.3f}')"; }

measure_warm() {
  export PATH="${HOME}/.local/bin:${HOME}/.hermes/bin:${PATH}"
  if ! command -v hermes >/dev/null 2>&1; then
    echo "n/a"
    return
  fi
  local t0
  t0="$(now)"
  hermes --version >/dev/null 2>&1 || true
  elapsed "$t0"
}

measure_cold() {
  if [[ "$SKIP_COLD" == "1" ]]; then
    echo "skipped"
    return
  fi
  local tmp t0
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/torii-hermes-cold.XXXXXX")"
  (
    export HOME="$tmp"
    export PATH="${HOME}/.local/bin:${HOME}/.hermes/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    t0="$(now)"
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh \
      | bash -s -- --skip-setup --commit "$PIN" --force-commit
    command -v hermes >/dev/null
    hermes --version >/dev/null
    elapsed "$t0"
  )
  rm -rf "$tmp"
}

measure_tarball() {
  local pack_tar restore_home t0
  pack_tar="$(mktemp "${TMPDIR:-/tmp}/torii-hermes-XXXXXX.tgz")"
  restore_home="$(mktemp -d "${TMPDIR:-/tmp}/torii-hermes-restore.XXXXXX")"
  export PATH="${HOME}/.local/bin:${HOME}/.hermes/bin:${PATH}"

  # Pack only Hermes install trees (not entire ~/.local — huge / sockets)
  if [[ -d "${HOME}/.hermes" ]]; then
    (
      cd "$HOME"
      # shellcheck disable=SC2035
      tar -czf "$pack_tar" \
        --exclude='*.sock' --exclude='sock' --exclude='*.pid' \
        .hermes \
        $( [[ -x .local/bin/hermes ]] && echo .local/bin/hermes ) \
        $( [[ -d .local/share/uv ]] && echo .local/share/uv ) \
        2>/dev/null || tar -czf "$pack_tar" .hermes
    )
  else
    echo "n/a"
    rm -rf "$restore_home" "$pack_tar"
    return
  fi

  if [[ ! -s "$pack_tar" ]]; then
    echo "n/a"
    rm -rf "$restore_home" "$pack_tar"
    return
  fi

  BENCH_TAR_BYTES="$(wc -c <"$pack_tar" | tr -d ' ')"
  export BENCH_TAR_BYTES
  t0="$(now)"
  tar -xzf "$pack_tar" -C "$restore_home"
  (
    export HOME="$restore_home"
    export PATH="${HOME}/.local/bin:${HOME}/.hermes/bin:/usr/bin:/bin"
    if command -v hermes >/dev/null 2>&1; then
      hermes --version >/dev/null 2>&1 || true
    fi
  )
  elapsed "$t0"
  rm -rf "$restore_home" "$pack_tar"
}

measure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "n/a"
    return
  fi
  local img="$IMAGE"
  if ! docker image inspect "$img" >/dev/null 2>&1; then
    if docker image inspect "${IMAGE_BASE}:latest" >/dev/null 2>&1; then
      img="${IMAGE_BASE}:latest"
    else
      echo "n/a"
      return
    fi
  fi
  local t0
  t0="$(now)"
  docker run --rm "$img" hermes --version >/dev/null
  elapsed "$t0"
}

log "=== Torii Hermes startup benchmark ==="
log "pin=$PIN image=$IMAGE skip_cold=$SKIP_COLD"

WARM_S="$(measure_warm)"
log "warm_present_s=$WARM_S"

log "measuring tarball restore (Actions cache proxy)..."
BENCH_TAR_BYTES=0
TARBALL_S="$(measure_tarball)"
log "tarball_restore_s=$TARBALL_S tar_bytes=${BENCH_TAR_BYTES:-0}"

DOCKER_S="$(measure_docker)"
log "docker_prebake_s=$DOCKER_S"

if [[ "$SKIP_COLD" == "1" ]]; then
  COLD_S="skipped"
  log "cold_install skipped (SKIP_COLD=1)"
else
  log "measuring cold install (may take several minutes)..."
  COLD_S="$(measure_cold)" || COLD_S="failed"
  log "cold_install_s=$COLD_S"
fi

mkdir -p "$(dirname "$BENCH_OUT")"
python3 - "$BENCH_OUT" "$PIN" "$WARM_S" "$TARBALL_S" "$DOCKER_S" "$COLD_S" "$IMAGE" "${BENCH_TAR_BYTES:-0}" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path

out, pin, warm, tarball, docker, cold, image, tar_bytes = sys.argv[1:9]

def num(x):
    try:
        return float(x)
    except Exception:
        return x

data = {
    "benchmark": "torii-hermes-startup",
    "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "hermes_pin": pin,
    "runner_image": image,
    "tarball_bytes": int(tar_bytes) if str(tar_bytes).isdigit() else tar_bytes,
    "seconds": {
        "warm_present": num(warm),
        "tarball_restore": num(tarball),
        "docker_prebake": num(docker),
        "cold_install": num(cold),
    },
    "notes": {
        "warm_present": "hermes --version when already installed (CI cache hit path)",
        "tarball_restore": "unpack packed ~/.local+~/.hermes (proxy for Actions cache restore)",
        "docker_prebake": "docker run prebaked image hermes --version (F8)",
        "cold_install": "isolated HOME full install.sh (CI cold miss)",
    },
}
Path(out).parent.mkdir(parents=True, exist_ok=True)
Path(out).write_text(json.dumps(data, indent=2) + "\n")
print(json.dumps(data, indent=2))

md = Path(str(out).removesuffix(".json") + ".md")
s = data["seconds"]
md.write_text(
    "\n".join(
        [
            "# Hermes startup benchmark",
            "",
            f"- **at:** `{data['at']}`",
            f"- **pin:** `{data['hermes_pin']}`",
            f"- **image:** `{data['runner_image']}`",
            f"- **tarball_bytes:** `{data.get('tarball_bytes')}`",
            "",
            "| Path | Seconds | Meaning |",
            "|------|--------:|---------|",
            f"| cold_install | {s['cold_install']} | Full install.sh in empty HOME |",
            f"| tarball_restore | {s['tarball_restore']} | Unpack pre-packed install (≈ Actions cache) |",
            f"| docker_prebake | {s['docker_prebake']} | Prebaked runner image |",
            f"| warm_present | {s['warm_present']} | Hermes already on PATH |",
            "",
            "Lower is better for job startup. Prefer **cache hit** or **prebaked image** over cold install.",
            "",
            "## How to reproduce",
            "",
            "```bash",
            "./scripts/build-torii-runner-image.sh   # optional Docker prebake",
            "./scripts/benchmark-hermes-startup.sh  # or SKIP_COLD=1 for quick paths only",
            "```",
            "",
        ]
    )
)
print("wrote", md, file=sys.stderr)
PY

log "Results → $BENCH_OUT"
