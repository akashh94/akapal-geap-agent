#!/usr/bin/env bash

set -euo pipefail

export PROJECT_ID="labs-gcp-msls-16495-1782829337"
export REGION="us-east1"
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/geap-ui-beta/geap-ui-beta:$(git rev-parse --short HEAD)"

# update the name as per the branch
gcloud run deploy geap-ui-beta \
  --image "$IMAGE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --min-instances 1 \
  --max-instances 1 \
  --set-env-vars NODE_ENV=production,ETRADE_ENV=sandbox,GEAP_ENGINE_ID=1675708497288757248