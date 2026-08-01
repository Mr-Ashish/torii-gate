#!/usr/bin/env bash
# F32: unified entry to start a Torii Gate review (local | modal | print commands).
#
# Usage:
#   ./scripts/trigger-review.sh print  owner/repo 123
#   ./scripts/trigger-review.sh local  owner/repo 123 [--model M] [--post]
#   ./scripts/trigger-review.sh modal  owner/repo 123 [--model M] [--post|--no-post]
#   ./scripts/trigger-review.sh help
#
# Env:
#   TORII_MODEL / OPENROUTER_MODEL  default model (local uses script default if unset)
#   OPENROUTER_API_KEY              required for local
#   POST_COMMENT=1                  same as --post
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-}"
shift || true

usage() {
  cat <<'EOF'
trigger-review.sh — start a Torii PR review

  print  owner/repo PR   Print local + modal commands (no spend)
  local  owner/repo PR    Run scripts/review-local.sh in this tree
  modal  owner/repo PR    modal run modal_app/app.py --bit 3 …
  help                    This help

Options (local|modal):
  --model ID       OpenRouter model id
  --post           Post PR comment (local: POST_COMMENT=1; modal: default on)
  --no-post        Modal only: skip PR comment
  --cheap          Shorthand model openai/gpt-4.1-mini (modal cheap profile)

Examples:
  ./scripts/trigger-review.sh print Mr-Ashish/odoo 3
  ./scripts/trigger-review.sh local  Mr-Ashish/odoo 3 --model openai/gpt-4.1-mini
  ./scripts/trigger-review.sh modal  Mr-Ashish/odoo 3 --cheap --no-post
EOF
}

if [[ -z "$MODE" || "$MODE" == "help" || "$MODE" == "-h" || "$MODE" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 $MODE owner/repo PR_NUMBER [options]" >&2
  exit 1
fi

REPO="$1"
PR="$2"
shift 2

MODEL="${TORII_MODEL:-${OPENROUTER_MODEL:-}}"
POST="${POST_COMMENT:-}"
NO_POST=0
CHEAP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="${2:-}"
      shift 2
      ;;
    --post)
      POST=1
      shift
      ;;
    --no-post)
      NO_POST=1
      POST=0
      shift
      ;;
    --cheap)
      CHEAP=1
      MODEL="${MODEL:-openai/gpt-4.1-mini}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [[ ! "$REPO" =~ ^[^/]+/[^/]+$ ]]; then
  echo "REPO must be owner/name, got: $REPO" >&2
  exit 1
fi
if ! [[ "$PR" =~ ^[0-9]+$ ]]; then
  echo "PR must be a number, got: $PR" >&2
  exit 1
fi

if [[ "$CHEAP" == "1" && -z "$MODEL" ]]; then
  MODEL="openai/gpt-4.1-mini"
fi

local_cmd() {
  local parts=( "./scripts/review-local.sh" "$REPO" "$PR" )
  local envp=()
  if [[ -n "$MODEL" ]]; then
    envp+=( "TORII_MODEL=$MODEL" )
  fi
  if [[ "${POST:-0}" == "1" ]]; then
    envp+=( "POST_COMMENT=1" )
  fi
  if [[ ${#envp[@]} -gt 0 ]]; then
    echo "${envp[*]} ${parts[*]}"
  else
    echo "${parts[*]}"
  fi
}

modal_cmd() {
  local parts=(
    "modal" "run" "modal_app/app.py"
    "--bit" "3"
    "--repo" "$REPO"
    "--pr" "$PR"
  )
  if [[ -n "$MODEL" ]]; then
    parts+=( "--model" "$MODEL" )
  elif [[ "$CHEAP" == "1" ]]; then
    parts+=( "--model" "openai/gpt-4.1-mini" )
  fi
  if [[ "$NO_POST" == "1" || "${POST:-1}" == "0" ]]; then
    # modal CLI bool: --no-post-comment when False default is True in app
    parts+=( "--no-post-comment" )
  fi
  echo "${parts[*]}"
}

case "$MODE" in
  print)
    echo "# local (needs OPENROUTER_API_KEY + gh auth)"
    local_cmd
    echo "# modal cheap worker (needs modal auth + secrets torii-openrouter, torii-github)"
    modal_cmd
    echo "# modal enqueue dry plan (bit 4, no Hermes spend)"
    echo "modal run modal_app/app.py --bit 4 --repo $REPO --pr $PR${MODEL:+ --model $MODEL}"
    ;;
  local)
    if [[ -f "$ROOT/.env" ]]; then
      set -a
      # shellcheck disable=SC1091
      source "$ROOT/.env"
      set +a
    fi
    export REPO PR_NUMBER="$PR"
    if [[ -n "$MODEL" ]]; then
      export TORII_MODEL="$MODEL"
      export OPENROUTER_MODEL="$MODEL"
    fi
    if [[ "${POST:-0}" == "1" ]]; then
      export POST_COMMENT=1
    fi
    exec "$ROOT/scripts/review-local.sh" "$REPO" "$PR"
    ;;
  modal)
    if ! command -v modal >/dev/null 2>&1; then
      echo "modal CLI not found — pip install modal && modal token new" >&2
      exit 1
    fi
    # F80: bootstrap torii-* Modal secrets from .env / gh auth (idempotent)
    if [[ -f "$ROOT/scripts/modal_secrets_bootstrap.py" ]]; then
      if ! python3 "$ROOT/scripts/modal_secrets_bootstrap.py" status >/dev/null 2>&1; then
        echo "F80: creating Modal secrets torii-openrouter / torii-github …" >&2
        python3 "$ROOT/scripts/modal_secrets_bootstrap.py" apply || \
          echo "WARN: secret bootstrap failed — see: python3 scripts/modal_secrets_bootstrap.py plan" >&2
      fi
    fi
    args=( run modal_app/app.py --bit 3 --repo "$REPO" --pr "$PR" )
    if [[ -n "$MODEL" ]]; then
      args+=( --model "$MODEL" )
    fi
    if [[ "$NO_POST" == "1" || "${POST:-1}" == "0" ]]; then
      args+=( --no-post-comment )
    fi
    cd "$ROOT"
    exec modal "${args[@]}"
    ;;
  *)
    echo "Unknown mode: $MODE (use print|local|modal|help)" >&2
    exit 1
    ;;
esac
