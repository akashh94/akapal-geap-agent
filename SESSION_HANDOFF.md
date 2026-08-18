# Session Handoff — GEAP Agent / Financial Planner Deployment (2026-08-17/18)

## Current state (verified working) — Model A (Cloud Run)

**Architecture: planner on Cloud Run, supervisor on Agent Engine**

- **MCP portfolio** (repo: `D:\vscode_projects\akapal-mcp-portfolio`)
  - Live at `https://mcp-portfolio-947331501288.us-central1.run.app/mcp`
  - Streamable HTTP transport only (`mcp.run(transport="streamable-http")`)
  - 9 tools verified live
- **Financial planner** (repo: `D:\vscode_projects\akapal-geap-financial-planner`)
  - **Cloud Run service**: `akapal-financial-planner`
  - URL: `https://akapal-financial-planner-947331501288.us-central1.run.app`
  - A2A base: `.../a2a/financial_planner`
  - **Standard card works**: `.../a2a/financial_planner/.well-known/agent-card.json` → 200, 16 skills, advertises `https://.../a2a/financial_planner`
  - Direct JSON-RPC `SendMessage` → 200 with real LLM answers
  - **Image**: `us-central1-docker.pkg.dev/adk-tut-499512/akapal-geap-ui/akapal-financial-planner:modela-v3`
  - **Deps pinned** in pyproject.toml: `google-adk==2.6.2`, `google-genai==2.17.0`, `google-cloud-aiplatform==1.163.0`
- **GEAP supervisor** (repo: `D:\vscode_projects\akapal-geap-agent`)
  - Engine: `5062056426524901376` (akapal-geap-agents)
  - **REDEPLOYED 2026-08-18** (twice): first with the a2a-sdk client tool + Cloud Run planner URL; then with the MCP Streamable-HTTP fix
  - Deployed env verified: `MCP_PORTFOLIO_URL` = live `/mcp`, `FINANCIAL_PLANNER_URL` = Cloud Run card
  - A2A card live at `.../api/a2a/supervisor/.well-known/agent-card.json` (200)
  - Card skills include `call_financial_planner` (the new tool is deployed)
  - **MCP connection verified**: `StreamableHTTPConnectionParams` discovers all 9 portfolio tools from the deployed server
- **Planner prompt fixed** (2026-08-18): now proactively calls `get_account_summary` / `get_portfolio_holdings` for current savings, uses defaults (age 40, 7%, 4% rule) instead of asking, and completes the projection. Verified: "Can I retire in 10 years if I save $1,000/mo?" → pulls $238,846.12 live balance, projects $654,094.29 nest egg, answers fully.
- **`planning_calculator.py` inf fix**: `retirement_projection` returned `float("inf")` for "never depletes" (when `monthly_withdrawal<=0`), which broke A2A JSON serialization (400 "Invalid JSON payload ... Infinity"). Now returns `999.0` sentinel (JSON-safe), `sustainable` still computed correctly.

## Full chain (all verified working)

```
supervisor (Agent Engine 5062056426524901376)
  → call_financial_planner tool (a2a-sdk client)
  → planner (Cloud Run akapal-financial-planner-947331501288.us-central1.run.app)
  → MCP portfolio (mcp-portfolio-947331501288.us-central1.run.app/mcp)
```

## Why the supervisor uses the a2a-sdk client (not RemoteA2aAgent)

`RemoteA2aAgent` (the ADK sub-agent) fails against the Cloud Run planner with:
```
part_metadata parameter is only supported in Gemini Developer API mode,
not in Gemini Enterprise Agent Platform mode.
```
Root cause: `RemoteA2aAgent` sends the message through ADK's A2A conversion which
sets `part_metadata` server-side on the planner's model call; Vertex rejects it.
The **plain a2a-sdk client** (`ClientFactory` + `send_message`, exactly what
curl-verified JSON-RPC does) works: verified "Hello." round-trip.

## Deploying the planner to Cloud Run

No bash on this Windows box — use PowerShell. The script `deploy.personal.cloudrun.sh`
encodes the steps; the manual equivalents:

```powershell
$env:IMAGE='us-central1-docker.pkg.dev/adk-tut-499512/akapal-geap-ui/akapal-financial-planner:modela-v3'
Set-Location 'D:\vscode_projects\akapal-geap-financial-planner'
docker build -t $env:IMAGE .
docker push $env:IMAGE
gcloud run deploy akapal-financial-planner --image $env:IMAGE --project adk-tut-499512 --region us-central1 --platform managed --allow-unauthenticated --port 8080 --min-instances 1 --max-instances 1 --update-env-vars "AGENT_MODEL=gemini-2.5-flash,MODEL_LOCATION=global,MCP_PORTFOLIO_URL=https://mcp-portfolio-947331501288.us-central1.run.app/mcp,GOOGLE_CLOUD_PROJECT=adk-tut-499512,GOOGLE_CLOUD_LOCATION=us-central1,APP_URL=https://akapal-financial-planner-947331501288.us-central1.run.app"
```

**Required env vars for Cloud Run (the app crashes without them):**
- `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` — `get_fast_api_app()` requires them (Agent Engine injected them automatically; Cloud Run doesn't)
- `APP_URL` — must be the **https** public URL, or the card advertises `http://` and A2A clients get a 302 redirect loop

## Deploying the supervisor (agents-cli)

```powershell
cd /d D:\vscode_projects\akapal-geap-financial-planner   # agents-cli is here
set VIRTUAL_ENV=
C:\Users\palro\.local\bin\agents-cli.exe deploy --deployment-target agent_runtime --project adk-tut-499512 --region us-central1 --update-env-vars "AGENT_MODEL=gemini-2.5-flash,MODEL_LOCATION=global,MCP_PORTFOLIO_URL=https://mcp-portfolio-947331501288.us-central1.run.app/mcp,FINANCIAL_PLANNER_URL=https://akapal-financial-planner-947331501288.us-central1.run.app/a2a/financial_planner/.well-known/agent-card.json" --no-confirm-project
```

`deploy.personal.env` (gitignored) already has the Cloud Run URL.

## Key files changed this session

### Planner repo
- **`pyproject.toml`** — pinned `google-adk==2.6.2`, `google-genai==2.17.0`, `google-cloud-aiplatform==1.163.0` (fixes the `part_metadata` / feature-flag drift)
- **`deploy.personal.cloudrun.sh`** — NEW: Cloud Run deploy script
- **`deploy.personal.env`** — added `ARTIFACT_REGION`, `SERVICE_NAME`
- **`app/agents/financial_planner_agent.py`** — `MCPToolset` (canonical name), `StreamableHTTPConnectionParams`, live MCP URL default
- **`app/deploy_a2a.py`** — Model B deploy script (kept for reference; NOT used for Model A)
- Docs updated (A2A_ARCHITECTURE, GUIDE, TROUBLESHOOTING)

### Agent repo
- **`app/tools/a2a_planner_tool.py`** — RESTORED a2a-sdk client tool (deleted in the Model B migration); adapted for Cloud Run (no URL rewrite)
- **`app/agents/supervisor.py`** — uses `financial_planner_tool` again (not the RemoteA2aAgent sub-agent)
- **`app/prompts/supervisor_prompt.py`** — references `call_financial_planner` tool again
- **`app/agents/financial_planner_agent.py`** — DELETED (RemoteA2aAgent unused)
- **`deploy.personal.env`** / **`geap.deploy.env`** — `FINANCIAL_PLANNER_BASE_URL` → Cloud Run URL, card at standard path
- **`app/app_utils/resilient_mcp.py`** — ruff formatting fix
- **`README.md`** — Model A docs

## Troubleshooting log (all resolved this session)

### 1. `mcp 2.0.0` broke `MCPToolset` import
Pin `mcp>=1.24,<2` (planner pyproject).

### 2. Planner used SSE but MCP portfolio is Streamable HTTP
`SseConnectionParams` → `StreamableHTTPConnectionParams`, live URL. (Model B era)

### 3. Model B: A2A operations didn't register (protobuf request types)
`_make_a2a_operations_registrable()` monkey-patch — **moot now**, Model A doesn't pickle.

### 4. Model B: card 404 / wrong engine ID
The platform only proxies registered operations; standard card path impossible.
**Moot now** — Model A's FastAPI serves the standard card directly.

### 5. Cloud Run container failed to start — `No GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION`
`get_fast_api_app()` requires these; Cloud Run doesn't inject them. Fix: set both in `--update-env-vars`.

### 6. A2A client got 302 redirect — card advertised `http://`
`APP_URL` unset → card advertised `http://...`; Cloud Run only serves `https`. Fix: set `APP_URL=https://<service-url>`.

### 7. `part_metadata` error on model call (the big one)
`RemoteA2aAgent` → planner model call fails: "part_metadata parameter is only supported in Gemini Developer API mode, not in Gemini Enterprise Agent Platform mode."
Investigation (all ruled out):
- NOT ADK version (2.6.2 vs 2.7.1 both failed)
- NOT genai version
- NOT aiplatform version (1.163.0 vs 1.164.0)
- NOT `full_history_when_stateless`
- NOT `use_legacy` (both True/False fail)
- Direct curl JSON-RPC **works**; a2a-sdk `ClientFactory` **works** ("Hello.")
**Fix: use the plain a2a-sdk client** (`app/tools/a2a_planner_tool.py`) instead of `RemoteA2aAgent`. The ADK A2A conversion path sets `part_metadata` that Vertex Enterprise rejects; the raw JSON-RPC path doesn't.

### 8. Supervisor MCP connection failed (400 / 301s / 409s to mcp-portfolio)
The supervisor's `api_registry_mcp.py` connected via **`SseConnectionParams`** but
the deployed portfolio server only speaks **Streamable HTTP** at `/mcp`. Symptoms
in Cloud Run logs: SSE session hitting the 300s request timeout (301s latency),
then 409 Conflict while the dead stream lingered, then 400 handshake failures.
Fix: `SseConnectionParams` → `StreamableHTTPConnectionParams` in
`build_portfolio_mcp_toolset()` + local default URL `/sse` → `/mcp`. Verified:
all 9 portfolio tools discover. (The "mTLS was requested..." log line is a
benign ADK warning, not an error.)

### 9. PowerShell gotchas on this box
- `cmd /c set X=... &` leaves trailing spaces (`'us-central1 '` breaks `vertexai.init`)
- Python stdout lost in background cmd — use `python -u` + `Out-File`
- `bash.exe` is the WSL launcher (no distro) — use PowerShell for everything
- `docker run ... python -c "..."` nested quotes break — write scripts to files instead

## Known remaining work
1. **IAM on the planner**: the planner Cloud Run service is `--allow-unauthenticated`, so no IAM needed. If the supervisor's tool call 403s on the planner, verify the planner service is still allow-unauthenticated (or grant `roles/run.invoker` to `service-947331501288@gcp-sa-aiplatform-re.iam.gserviceaccount.com`).
2. **Stale engines cleaned up** (2026-08-18): deleted `2088431627251220480`, `2889157567248859136`, `4185068360024719360`, `7964503241062875136`. Kept:
   - `5062056426524901376` (the supervisor, active)
   - `9122139451529625600` (final Model B planner, kept per request — not referenced by anything)
3. **Office env** (`geap.deploy.env` in planner repo) still has placeholder/SSE values — update before office deploys
4. `deploy.personal.cloudrun.sh` is a bash script — can't run on this box; the PowerShell steps above are the working path
5. **agents-cli version mismatch warning**: project scaffolded with 1.2.1, running 1.3.1 — `agents-cli scaffold upgrade` is optional
6. **Deploy gotcha**: passing `MCP_REGISTRY_SERVER=` (empty) in `--update-env-vars` fails with "Required field is not set" — drop empty vars from the deploy command

## Useful commands
```bash
# Fetch the planner card (public, no auth needed)
curl https://akapal-financial-planner-947331501288.us-central1.run.app/a2a/financial_planner/.well-known/agent-card.json

# A2A round trip (public)
curl -X POST -H "Content-Type: application/json" -H "A2A-Version: 1.0" \
  -d '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":{"message":{"role":"ROLE_USER","messageId":"t1","parts":[{"text":"Say hi"}]}}}' \
  https://akapal-financial-planner-947331501288.us-central1.run.app/a2a/financial_planner

# Cloud Run logs
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=akapal-financial-planner' --project=adk-tut-499512 --limit=30 --format='value(textPayload)'
```
