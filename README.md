# geap-agent

GEAP Agent — an ADK-powered multi-agent financial advisor. A single "supervisor"
agent orchestrates a team of specialist sub-agents (portfolio, trading, market
research, customer support, mortgage) and is exposed over both the standard ADK
web/API surface and the A2A (Agent2Agent) protocol.

## Architecture

- **`app/agent.py`** — entry point exposing `root_agent` for ADK web UI discovery.
- **`app/agents/supervisor.py`** — the `supervisor` root agent that routes to sub-agents.
- **`app/agents/`** — specialist agents: `portfolio_analyst`, `trade_assistant`,
  `market_research`, `customer_support`, `mortgage_agent`.
- **`app/tools/a2a_planner_tool.py`** — `call_financial_planner` tool: delegates
  financial-planning questions to the remote planner via the **a2a-sdk client**
  against the planner's Agent Engine A2A passthrough (Bearer-token auth, card
  URL rewrite to the public passthrough base).
- **`app/fast_api_app.py`** — FastAPI app wiring the runner, sessions, A2A routes,
  `/feedback` endpoint, and Cloud Logging.
- **`app/app_utils/a2a.py`** — `attach_a2a_routes()`: registers the A2A agent card and
  JSON-RPC endpoints under `/a2a/<agent_name>`.
- **`app/config/models.py`** — shared Gemini model config (reads `AGENT_MODEL` /
  `MODEL_LOCATION`; retries on 429/5xx with exponential backoff).
- **`agents-cli-manifest.yaml`** — manifest for `agents-cli` deployment (Agent Engine).

```
user ──▶ /api (ADK web/API)        ──▶ Runner ──▶ supervisor
        /a2a/supervisor/ (A2A RPC) ──▶ A2aAgentExecutor ──▶ Runner ──▶ supervisor
                                                                         │
                                              ┌──────────┬──────────────┼─────────────┐
                                         portfolio    trade    market_research  support  mortgage
                                                                         │
                                                              MCP portfolio server
```

## Requirements

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) (recommended; a `uv.lock` is committed)
- Google Cloud credentials with access to the model configured in `AGENT_MODEL`
  (the app runs locally without them, but agent calls need them)

## Local development

```bash
uv sync          # install dependencies from uv.lock
uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000 --reload
```

Without `uv`:

```bash
pip install -e .
uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000 --reload
```

The app loads `.env` at startup. A minimal `.env` looks like:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
AGENT_MODEL=gemini-2.5-flash
MODEL_LOCATION=global
MCP_PORTFOLIO_URL=http://localhost:8080/sse
```

### What comes up

| Endpoint | Description |
| --- | --- |
| `http://localhost:8000/docs` | FastAPI interactive docs |
| `http://localhost:8000/dev-ui/` | ADK web UI — interactive agent playground (chat, debug, eval, graph) |
| `http://localhost:8000/api/` | ADK web/API routes |
| `http://localhost:8000/a2a/supervisor` | A2A JSON-RPC endpoint |
| `http://localhost:8000/a2a/supervisor/.well-known/agent-card.json` | A2A agent card |
| `POST http://localhost:8000/feedback` | Log feedback |

### Notes

- Several sub-agents connect to an MCP portfolio server at `MCP_PORTFOLIO_URL`
  (default `http://localhost:8080/sse`). The app starts without it, but those
  agents fail when invoked until the MCP server is up.
- `vertexai.init()` and Cloud Logging degrade gracefully with warnings if
  credentials are missing.

## Calling the agent via A2A

Any A2A-compliant client (Gemini Enterprise, another ADK agent) can invoke the
agent:

1. **Discover** — `GET /a2a/supervisor/.well-known/agent-card.json` for the agent
   card.
2. **Send a message** — `POST /a2a/supervisor` with a JSON-RPC body (the A2A
   method is `SendMessage`; the legacy `message/send` draft name is rejected):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "SendMessage",
  "params": {
    "message": {
      "role": "ROLE_USER",
      "messageId": "msg-1",
      "parts": [{ "text": "What's my portfolio worth?" }]
    }
  }
}
```

Streaming clients use `SendStreamingMessage`. The A2A routes share the same
`Runner` (and thus the same sessions/artifacts) as the main ADK path.

> **Note:** the A2A endpoints have no authentication. The `ALLOW_ORIGINS` env var
> only affects browser CORS. Add auth middleware before exposing publicly.

## Configuration

| Env var | Default | Purpose |
| --- | --- | --- |
| `GOOGLE_CLOUD_PROJECT` | — | GCP project (also used for Vertex AI init) |
| `GOOGLE_CLOUD_LOCATION` | — | GCP region |
| `AGENT_MODEL` | `gemini-2.5-flash` | Model used by all agents |
| `MODEL_LOCATION` | `global` | Vertex AI endpoint location for model calls |
| `MCP_PORTFOLIO_URL` | `http://localhost:8080/sse` | MCP portfolio server (SSE) |
| `FINANCIAL_PLANNER_URL` | `https://PLACEHOLDER...` | A2A agent-card URL of the remote financial planner (Agent Engine passthrough) |
| `APP_URL` | `http://0.0.0.0:8000` | Base URL advertised on the A2A agent card |
| `AGENT_VERSION` | `0.1.0` | Version advertised on the A2A agent card |
| `ALLOW_ORIGINS` | — | Comma-separated CORS origins (browser only) |

### Config var details

- **`GOOGLE_CLOUD_PROJECT`** — Your GCP project ID. Used for `vertexai.init()` and
  Cloud Logging at startup. On Agent Engine / Cloud Run this is resolved
  automatically from the service identity, so you normally don't set it in the
  deployed environment. Set it locally (or in `.env`) to match your project.
  Read in `app/fast_api_app.py` and `app/app_utils/services.py`.

- **`GOOGLE_CLOUD_LOCATION`** — GCP region, e.g. `us-central1`. Used by
  `services.py` for the Vertex AI session service when running on Agent
  Engine. Note `MODEL_LOCATION` (below) is separate — it controls which Vertex
  endpoint the model calls route to, not where the app runs.

- **`AGENT_MODEL`** — The Gemini model used by *every* agent (supervisor and
  sub-agents). Default `gemini-2.5-flash` (the cheapest Gemini text model).
  Read at call time by `app/config/models.py`, so you can change it via the
  deployment env vars without rebuilding the container.

- **`MODEL_LOCATION`** — Vertex AI endpoint location for model calls. Default
  `global`, which spreads load across regions and avoids dynamic shared-quota
  throttling on regional endpoints. The Agent Engine instance still lives in
  its configured region; only model requests go global.

- **`MCP_PORTFOLIO_URL`** — SSE URL of the MCP portfolio server used by the
  portfolio/trade/market-research/support agents via `ResilientMcpToolset`.
  Default `http://localhost:8080/sse` for local dev. In the deployed personal
  project this is `https://mcp-portfolio-a3wvlai7eq-uc.a.run.app/sse`. The
  agents degrade gracefully (an informational tool) if the server is
  unreachable — they won't crash the turn.

- **`FINANCIAL_PLANNER_URL`** — A2A agent-card URL of the separately-deployed
  financial planner that the supervisor reaches through the
  `call_financial_planner` tool (`app/tools/a2a_planner_tool.py`). For a
  planner on **Vertex AI Agent Engine**, this is the HTTP passthrough card URL:

  ```
  https://<location>-aiplatform.googleapis.com/reasoningEngines/v1/
    projects/<project>/locations/<location>/reasoningEngines/<id>/
    api/a2a/financial_planner/.well-known/agent-card.json
  ```

  The tool authenticates with a Bearer token from ambient credentials and
  rewrites the card's advertised (internal) URL to the public passthrough base
  before sending. The placeholder default fails loudly on first use until you
  set it. Each call uses a fresh message/task (stateless by design).

- **`APP_URL`** — Base URL advertised on the A2A agent card (used to build the
  card's `rpcUrl`). Default `http://0.0.0.0:8000`; set it to the deployed
  service's public URL so A2A clients can find the JSON-RPC endpoint.

- **`AGENT_VERSION`** — Version string advertised on the A2A agent card.
  Default `0.1.0`. Bump it when you ship a deploy so clients can see the
  change.

- **`ALLOW_ORIGINS`** — Comma-separated CORS origins, browser-only. The A2A
  endpoints have **no authentication**; this does not secure them. Add auth
  middleware before exposing publicly.

- **`LOGS_BUCKET_NAME`** — (optional) GCS bucket for prompt/response logging.
  When set together with `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`,
  `setup_telemetry()` (`app/app_utils/telemetry.py`) enables GenAI
  prompt-response logging to `gs://<bucket>/completions`. Without it, logging
  falls back to Cloud Logging metadata only.

- **`SESSION_SERVICE_URI`** — (advanced) Override the session service used by
  `services.py`. Defaults to in-memory, or to the Vertex AI session service
  when `GOOGLE_CLOUD_AGENT_ENGINE_ID` is present. Set this only if you want a
  specific session backend (e.g. a SQL/Redis URI).

- **`GOOGLE_CLOUD_AGENT_ENGINE_ID`** — (advanced, runtime-injected) Set by the
  Agent Engine platform at deploy time. `services.py` uses it (with
  `GOOGLE_CLOUD_AGENT_ENGINE_LOCATION`) to select the
  `VertexAiSessionService`, so sessions persist across the deployed
  containers. You normally don't set this by hand.

- **`GOOGLE_CLOUD_AGENT_ENGINE_LOCATION`** — (advanced, runtime-injected)
  Region of the Agent Engine instance, used with the engine ID above for
  session service location. Not the same as `MODEL_LOCATION`.

## Deployment

### Docker

```bash
docker build -t geap-agent .
docker run -p 8080:8080 --env-file .env geap-agent
```

The image runs `uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8080`.

### Google Cloud (Agent Engine)

The `agents-cli` manifest targets Agent Engine (`deployment_target: agent_runtime`).
Helper scripts are provided (run in Cloud Shell):

- `./build.sh` — installs `uv` + `agents-cli`, runs `agents-cli install` and lint.
- `./deploy.sh` — deploys via `agents-cli deploy --deployment-target agent_runtime`,
  overriding `AGENT_MODEL` / `MODEL_LOCATION` / `MCP_PORTFOLIO_URL` / `FINANCIAL_PLANNER_URL`.

For the personal `akapal-geap-ui` project (`adk-tut-499512` / `us-central1`,
Artifact Registry repo `akapal-geap-ui`):

- `./build.personal.sh` — same as build, but ensures the
  `akapal-geap-ui` Artifact Registry repo exists in the deploy region.
- `./deploy.personal.sh` — deploys with `AGENT_MODEL=gemini-2.5-flash`
  (the cheapest Gemini text model) and the project's own MCP portfolio
  service (`mcp-portfolio-a3wvlai7eq-uc.a.run.app`).

### Two environments, two self-contained env files

Each environment has its own complete env file — the same variables in both,
different values. Each script sources **exactly one** of them:

| Script | Sources | Environment |
|---|---|---|
| `./build.sh` / `./deploy.sh` | `geap.deploy.env` | Office (default project `labs-gcp-msls-16495-1782829337`, `us-east1`) |
| `./build.personal.sh` / `./deploy.personal.sh` | `deploy.personal.env` | Personal (`adk-tut-499512`, `us-central1`) |

Both files define the same variables (`PROJECT_ID`, `REGION`, `AGENT_MODEL`,
`MODEL_LOCATION`, `MCP_PORTFOLIO_URL`, `FINANCIAL_PLANNER_BASE_URL`,
`FINANCIAL_PLANNER_URL`) — so picking which file a script sources is what
picks which environment it deploys to. To point an environment at a different
financial planner, edit **only** that environment's file:

```bash
# deploy.personal.env — the planner's Agent Engine A2A passthrough base
FINANCIAL_PLANNER_BASE_URL=https://<location>-aiplatform.googleapis.com/reasoningEngines/v1/projects/<project>/locations/<location>/reasoningEngines/<id>/api/a2a/financial_planner
```

That single value derives `FINANCIAL_PLANNER_URL`
(`${FINANCIAL_PLANNER_BASE_URL}/.well-known/agent-card.json`), which the
supervisor's `call_financial_planner` tool (`app/tools/a2a_planner_tool.py`)
reads at runtime.

- `geap.deploy.env` is committed to version control.
- `deploy.personal.env` is **gitignored** — copy it per-machine and fill in
  your own values.

Any value can still be overridden per-run:
`PROJECT_ID=my-project ./deploy.sh`.

## Feedback

`POST /feedback` accepts a JSON body with the `Feedback` schema
(`app/app_utils/typing.py`) and logs it to Cloud Logging when available,
falling back to console logs.
