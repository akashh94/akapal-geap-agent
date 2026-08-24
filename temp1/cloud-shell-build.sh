#!/usr/bin/env bash

set -euo pipefail

#for the demo build the checked out branch should be main, and for the beta checkout release/beta branch
git pull

export PROJECT_ID="labs-gcp-msls-16495-1782829337"
export REGION="us-east1"
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/geap-ui-beta/geap-ui-beta:$(git rev-parse --short HEAD)"

echo "$IMAGE"

gcloud builds submit --tag "$IMAGE" --project "$PROJECT_ID"