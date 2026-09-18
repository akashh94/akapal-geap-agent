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

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found; installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# No environment config is needed here: the deploy is an SDK object deploy, so
# there is no container build and no Artifact Registry repository to provision.
# Agent Runtime builds the image. This script only has to install dependencies
# and keep the lint gate that used to block the deploy.
uv sync
uv run ruff format --check .
uv run ruff check .
