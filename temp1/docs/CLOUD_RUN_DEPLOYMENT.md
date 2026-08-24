# GEAP UI — Deployment to Cloud Run

This deploys the framework-free E*TRADE-like mock site (`server.js` +
`public/`) as a standalone container on **Cloud Run**. The GEAP agent (ADK
supervisor + specialists) now lives entirely in the separate `geap-agent`
repo and deploys to Vertex AI Agent Engine independently — all frontend API
calls in this repo are same-origin, so this UI can be built and deployed on
its own.

Run everything below from a Cloud Shell session with `gcloud` already
authenticated.

## 0. Prerequisites

- A GCP project you have editor/owner rights on
- This repo checked out in Cloud Shell

## 1. Clone the repo and set your target project

```bash
git clone git@github.com:MorganStanley-GIL/geap-poc.git   # or: git pull, if already cloned
cd geap-poc

export PROJECT_ID=<your-isolated-gcp-project-id>
export REGION=us-east1
gcloud config set project "$PROJECT_ID"
```

## 2. Enable required APIs

```bash
gcloud services enable run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project "$PROJECT_ID"
```

## 3. Create an Artifact Registry repo for the image (one-time)

```bash
gcloud artifacts repositories create geap-ui-beta \
  --repository-format=docker \
  --location="$REGION" \
  --description="GEAP E*TRADE POC UI" \
  --project "$PROJECT_ID"
```

## 4. Build and push the image with Cloud Build (no local Docker needed)

```bash
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/geap-ui-beta/geap-ui-beta:$(git rev-parse --short HEAD)"

gcloud builds submit --tag "$IMAGE" --project "$PROJECT_ID"
```

## 5. (Recommended) Put secrets in Secret Manager instead of plain env vars

The app reads `SESSION_SECRET`, `ETRADE_CONSUMER_KEY`, `ETRADE_CONSUMER_SECRET`
— set these up if you're wiring up real E*TRADE sandbox creds:

```bash
gcloud services enable secretmanager.googleapis.com --project "$PROJECT_ID"

echo -n "$(openssl rand -base64 32)" | gcloud secrets create session-secret --data-file=- --project "$PROJECT_ID"
echo -n "<your-etrade-consumer-key>"    | gcloud secrets create etrade-consumer-key --data-file=- --project "$PROJECT_ID"
echo -n "<your-etrade-consumer-secret>" | gcloud secrets create etrade-consumer-secret --data-file=- --project "$PROJECT_ID"
```

If you don't have E*TRADE sandbox creds yet, skip this step — the UI still
runs fine without them; only the "Connect to E*TRADE" login flow will show a
config error. Everything else (mock portfolio views, agent-studio, etc.)
works.

## 6. Deploy to Cloud Run

With secrets from step 5:

```bash
gcloud run deploy geap-ui-beta \
  --image "$IMAGE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --min-instances 1 \
  --max-instances 1 \
  --set-env-vars NODE_ENV=production,ETRADE_ENV=sandbox \
  --set-secrets SESSION_SECRET=session-secret:latest,ETRADE_CONSUMER_KEY=etrade-consumer-key:latest,ETRADE_CONSUMER_SECRET=etrade-consumer-secret:latest
```

Without secrets (skip `--set-secrets` entirely):

```bash
gcloud run deploy geap-ui-beta \
  --image "$IMAGE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --min-instances 1 \
  --max-instances 1 \
  --set-env-vars NODE_ENV=production,ETRADE_ENV=sandbox
```

**Why `--min-instances 1 --max-instances 1`:** the app keeps E*TRADE OAuth
session state in an in-memory `express-session` store. If Cloud Run scales to
multiple instances, a user can bounce between instances and lose their
session mid-login. Pinning to exactly one instance keeps this POC's session
behavior correct without rearchitecting session storage. Remove that
constraint (and route sessions through something like Memorystore/Firestore)
if you need real autoscaling later.

## 7. Get the URL and verify

```bash
gcloud run services describe geap-ui-beta --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)'
```

Open that URL — you should see the E*TRADE-style mock UI load.

## 8. Redeploying after changes

Repeat steps 4 and 6 (the image tag changes with each new commit SHA, so just
re-run both commands after committing your changes).
