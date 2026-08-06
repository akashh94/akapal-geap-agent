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
| `http://localhost:8000/a2a/supervisor/` | A2A JSON-RPC endpoint |
| `http://localhost:8000/a2a/supervisor/.well-known/agent.json` | A2A agent card |
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

1. **Discover** — `GET /a2a/supervisor/.well-known/agent.json` for the agent card
   (contains `rpcUrl`).
2. **Send a message** — `POST /a2a/supervisor/` with a JSON-RPC body:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{ "text": "What's my portfolio worth?" }]
    }
  }
}
```

Streaming clients use `message/stream` instead of `message/send`. The A2A routes
share the same `Runner` (and thus the same sessions/artifacts) as the main ADK
path.

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
| `APP_URL` | `http://0.0.0.0:8000` | Base URL advertised on the A2A agent card |
| `AGENT_VERSION` | `0.1.0` | Version advertised on the A2A agent card |
| `ALLOW_ORIGINS` | — | Comma-separated CORS origins (browser only) |

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

- `./cloud-shell-build.sh` — installs `uv` + `agents-cli`, runs `agents-cli install` and lint.
- `./cloud-shell-deploy.sh` — deploys via `agents-cli deploy --deployment-target agent_runtime`,
  overriding `AGENT_MODEL` / `MODEL_LOCATION` / `MCP_PORTFOLIO_URL`.

Set `PROJECT_ID` / `REGION` env vars to override the defaults
(`labs-gcp-msls-16495-1782829337` / `us-east1`).

## Feedback

`POST /feedback` accepts a JSON body with the `Feedback` schema
(`app/app_utils/typing.py`) and logs it to Cloud Logging when available,
falling back to console logs.
