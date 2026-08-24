#!/usr/bin/env bash
#
# Attaches this project's deployed Agent Runtime instance to an existing
# Agent Gateway in Client-to-Agent (ingress) mode, per:
# https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/agent-gateway-runtime-deploy#client-to-agent
#
# Prerequisites (not done by this script):
#   - The agent must already be deployed via cloud-shell-deploy.sh
#     (agents-cli deploy), producing deployment_metadata.json.
#   - The Agent Gateway resource itself must already exist in the same
#     project/region as the agent. See:
#     https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/gateways/set-up-agent-gateway
#
# Usage (run from Cloud Shell, in this directory):
#   AGENT_GATEWAY_NAME=my-ingress-gateway ./cloud-shell-agent-gateway-client-to-agent.sh
#
# Optional overrides:
#   PROJECT_ID                   GCP project (default: matches cloud-shell-deploy.sh)
#   REGION                       GCP region (default: matches cloud-shell-deploy.sh)
#   AGENT_RUNTIME_RESOURCE_NAME  Full reasoningEngines resource name, e.g.
#                                projects/P/locations/R/reasoningEngines/ID.
#                                Skips reading deployment_metadata.json.

set -euo pipefail

export PROJECT_ID="${PROJECT_ID:-labs-gcp-msls-16495-1782829337}"
export REGION="${REGION:-us-east1}"

if [[ -z "${AGENT_GATEWAY_NAME:-}" ]]; then
  echo "ERROR: AGENT_GATEWAY_NAME is not set." >&2
  echo "Set it to the short name of an existing Client-to-Agent Agent Gateway, e.g.:" >&2
  echo "  AGENT_GATEWAY_NAME=my-ingress-gateway $0" >&2
  exit 1
fi

for cmd in gcloud curl jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command '$cmd' not found." >&2
    exit 1
  fi
done

METADATA_FILE="$(dirname "$0")/deployment_metadata.json"

if [[ -n "${AGENT_RUNTIME_RESOURCE_NAME:-}" ]]; then
  RESOURCE_NAME="$AGENT_RUNTIME_RESOURCE_NAME"
elif [[ -f "$METADATA_FILE" ]]; then
  RESOURCE_NAME="$(jq -r '.remote_agent_runtime_id' "$METADATA_FILE")"
  if [[ -z "$RESOURCE_NAME" || "$RESOURCE_NAME" == "null" ]]; then
    echo "ERROR: could not read remote_agent_runtime_id from $METADATA_FILE" >&2
    exit 1
  fi
else
  echo "ERROR: $METADATA_FILE not found and AGENT_RUNTIME_RESOURCE_NAME not set." >&2
  echo "Run ./cloud-shell-deploy.sh first, or set AGENT_RUNTIME_RESOURCE_NAME explicitly." >&2
  exit 1
fi

# RESOURCE_NAME looks like: projects/P/locations/R/reasoningEngines/ID
RESOURCE_ID="${RESOURCE_NAME##*/}"

AGENT_GATEWAY_RESOURCE="projects/${PROJECT_ID}/locations/${REGION}/agentGateways/${AGENT_GATEWAY_NAME}"
API_URL="https://${REGION}-aiplatform.googleapis.com/v1beta1/${RESOURCE_NAME}?updateMask=spec.deploymentSpec.agentGatewayConfig"

echo "Attaching Agent Runtime ${RESOURCE_ID} to Client-to-Agent gateway ${AGENT_GATEWAY_RESOURCE}..."

RESPONSE="$(curl -sS -X PATCH \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "{
    \"spec\": {
      \"deploymentSpec\": {
        \"agentGatewayConfig\": {
          \"clientToAgentConfig\": {
            \"agentGateway\": \"${AGENT_GATEWAY_RESOURCE}\"
          }
        }
      }
    }
  }" \
  "$API_URL")"

echo "$RESPONSE" | jq .

if echo "$RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
  echo "ERROR: gateway attach request failed (see response above)." >&2
  exit 1
fi

echo
echo "Verifying..."
curl -sS -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://${REGION}-aiplatform.googleapis.com/v1beta1/${RESOURCE_NAME}" \
  | jq '.spec.deploymentSpec.agentGatewayConfig'
