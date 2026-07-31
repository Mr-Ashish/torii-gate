# F8: Prebaked GitHub Actions / local runner image with Hermes Agent installed.
# Speeds Torii CI by skipping cold Hermes install on every job.
#
# Build (from repo root):
#   ./scripts/build-torii-runner-image.sh
#
# Run:
#   docker run --rm ghcr.io/mr-ashish/torii-hermes-runner:latest hermes --version
#
# Pin must match scripts/hermes-pin.sh DEFAULT (or pass HERMES_COMMIT=...).
ARG HERMES_COMMIT=53559aaf86b84dadae83cd9bb605ca476f9a0606
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    TORII_HERMES_PREBAKED=1 \
    PATH="/root/.local/bin:/root/.hermes/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git python3 python3-venv bash \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Hermes at pinned commit (non-interactive)
ARG HERMES_COMMIT
RUN curl -fsSL https://hermes-agent.nousresearch.com/install.sh \
      | bash -s -- --skip-setup --commit "${HERMES_COMMIT}" --force-commit \
    && command -v hermes \
    && hermes --version \
    && printf '%s\n' "${HERMES_COMMIT}" >/root/.hermes-pin

LABEL org.opencontainers.image.title="torii-hermes-runner" \
      org.opencontainers.image.description="Torii CI runner with Hermes Agent preinstalled" \
      org.opencontainers.image.source="https://github.com/Mr-Ashish/torii-gate"

WORKDIR /workspace
CMD ["hermes", "--version"]
