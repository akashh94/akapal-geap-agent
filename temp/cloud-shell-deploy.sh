#!/usr/bin/env bash

set -euo pipefail

export PROJECT_ID="${PROJECT_ID:-labs-gcp-msls-16495-1782829337}"
export REGION="${REGION:-us-east1}"

# Matches app/config/models.py's build_model() defaults; override before
# running if you want the deployed agent to use a different model/location.
export AGENT_MODEL="${AGENT_MODEL:-gemini-3.5-flash}"
export MODEL_LOCATION="${MODEL_LOCATION:-global}"
# --update-env-vars only sets the keys it's given -- it doesn't clear vars
# left over from a previous deploy. planning_agent no longer defines its own
# pro-tier default (see app/config/models.py), so pin this explicitly on
# every deploy to overwrite any stale PLANNING_AGENT_MODEL baked into the
# live Agent Runtime environment from before that change.
export PLANNING_AGENT_MODEL="${PLANNING_AGENT_MODEL:-gemini-3.5-flash}"

# agents-cli-manifest.yaml has deployment_target set to "none" (never wired
# up), so it's overridden explicitly here. "agent_runtime" is the target that
# maps to the Vertex AI Agent Engine / Reasoning Engine resource that
# geap-poc/server.js already calls (GEAP_ENGINE_ID et al.).
agents-cli deploy \
  --deployment-target agent_runtime \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --update-env-vars "AGENT_MODEL=${AGENT_MODEL},MODEL_LOCATION=${MODEL_LOCATION},PLANNING_AGENT_MODEL=${PLANNING_AGENT_MODEL}" \
  --no-confirm-project
