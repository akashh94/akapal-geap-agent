#!/usr/bin/env bash

set -euo pipefail

git pull

export PROJECT_ID="${PROJECT_ID:-labs-gcp-msls-16495-1782829337}"
export REGION="${REGION:-us-east1}"

gcloud config set project "$PROJECT_ID"

# Unlike geap-poc (a plain Node/Cloud Run app), this agent has no standalone
# "build a container image" step of its own: `agents-cli deploy` builds and
# ships the agent in one shot for the agent_runtime target. This script just
# makes sure the toolchain is present and dependencies/lint are sane before
# cloud-shell-deploy.sh runs.

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found; installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v agents-cli >/dev/null 2>&1; then
  echo "agents-cli not found; installing via uv tool install..."
  uv tool install google-agents-cli
  export PATH="$HOME/.local/bin:$PATH"
fi

agents-cli install
agents-cli lint
