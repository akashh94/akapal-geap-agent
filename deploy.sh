#!/usr/bin/env bash

set -euo pipefail

# Run from this project's root, so pyproject.toml and uv.lock are found
# regardless of the cwd.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# uv resolves the project environment from VIRTUAL_ENV if set. When this script
# runs from a shell where a venv in a parent directory is active, uv complains
# that the interpreter is "outside the project directory". Unset it so uv uses
# the project-local .venv instead.
unset VIRTUAL_ENV

# Office environment config (self-contained): PROJECT_ID / REGION / AGENT_MODEL /
# MODEL_LOCATION / MCP_PORTFOLIO_URL / MCP_REGISTRY_SERVER /
# FINANCIAL_PLANNER_ENGINE / STAGING_BUCKET all come from geap.deploy.env — the
# single source of truth for the office deployment.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/geap.deploy.env"

# deploy_adk.py reads the SDK's variable names; the env file names them
# PROJECT_ID and REGION. This translation is the reason this wrapper exists
# rather than running the .py directly.
export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="$REGION"

uv run python deploy_adk.py
