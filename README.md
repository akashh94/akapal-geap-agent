# geap-agent

GEAP Agent — an ADK-powered multi-agent financial advisor. A single "supervisor"
agent orchestrates a team of specialist sub-agents (portfolio, trading, market
research, customer support, mortgage) and is deployed to **Agent Runtime** as an
ADK agent driven through the platform's `:query` / `:streamQuery` methods.

There is no HTTP server in this repo. The deploy is an SDK object deploy of a
`vertexai.agent_engines.AdkApp`, so the platform serves the agent's operations.

Long-term, cross-session memory is provided by Vertex AI Memory Bank — see
[docs/MEMORY_BANK.md](docs/MEMORY_BANK.md) for the full implementation guide.

Start with [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — the whole system (both
agents, the MCP server, memory) explained from first principles with diagrams.

How the supervisor and the separately-deployed financial planner reach each
other over A2A on Agent Runtime — including the deploy order, the required APIs
and IAM, and the failure modes to expect — is documented in
[docs/AGENT_RUNTIME_A2A.md](docs/AGENT_RUNTIME_A2A.md).

## Architecture

- **`app/agent.py`** — entry point exposing `root_agent`. Also runs the
  process-wide setup (dotenv, telemetry) at import, since this module is what the
  deployed `AdkApp` resolves.
- **`app/agents/supervisor.py`** — the `supervisor` root agent that routes to sub-agents.
- **`app/agents/`** — specialist agents: `portfolio_analyst`, `trade_assistant`,
  `market_research`, `customer_support`, `mortgage_agent`.
- **`app/tools/a2a_planner_tool.py`** — `call_financial_planner` FunctionTool:
  delegates financial-planning questions to the remote planner over A2A, via the
  Agent Platform SDK (`agent_engines.get` → `on_message_send`).
- **`app/app_utils/api_registry_mcp.py`** — builds the portfolio MCP toolset,
  preferring the Agent Registry entry over the raw URL.
- **`app/config/models.py`** — shared Gemini model config (reads `AGENT_MODEL` /
  `MODEL_LOCATION`; retries on 429/5xx with exponential backoff).
- **`deploy_adk.py`** — the object deploy (`AdkApp` + requirements + `app` package).

```
client ──▶ reasoningEngines :query / :streamQuery ──▶ supervisor
                                                          │
                               ┌──────────┬───────────────┼─────────────┐
                          portfolio    trade    market_research  support  mortgage
                                                          │
                                               MCP portfolio server
```

## Requirements

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) (recommended; a `uv.lock` is committed)
- Google Cloud credentials with access to the model configured in `AGENT_MODEL`
  (the agent loads without them, but model calls need them)

## Local development

```bash
uv sync
uv run adk web app      # ADK dev UI (chat, debug, eval, graph)
```

`app/` is a single-agent directory, so point ADK straight at it. The agent loads
`.env` at import. A minimal `.env` looks like:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
AGENT_MODEL=gemini-2.5-flash
MODEL_LOCATION=global
MCP_PORTFOLIO_URL=http://localhost:8080/mcp
```

Locally, sessions and memory are in-memory. After deploying, `AdkApp` switches to
Vertex AI sessions and Vertex AI Memory Bank automatically — see the
`GOOGLE_CLOUD_AGENT_ENGINE_ID` entry below.

### Notes

- Several sub-agents connect to an MCP portfolio server at `MCP_PORTFOLIO_URL`
  (default `http://localhost:8080/mcp`). The agent starts without it, and those
  agents degrade to an informational tool rather than failing the turn.
- `setup_telemetry()` and the Cloud Logging exporters degrade gracefully with
  warnings when credentials are missing.

## Configuration

| Env var | Default | Purpose |
| --- | --- | --- |
| `GOOGLE_CLOUD_PROJECT` | — | GCP project |
| `GOOGLE_CLOUD_LOCATION` | — | GCP region |
| `STAGING_BUCKET` | — | GCS bucket for object-deploy artifacts (deploy-time only) |
| `AGENT_MODEL` | `gemini-2.5-flash` | Model used by all agents |
| `MODEL_LOCATION` | `global` | Vertex AI endpoint location for model calls |
| `MCP_PORTFOLIO_URL` | `http://localhost:8080/mcp` | MCP portfolio server (fallback when `MCP_REGISTRY_SERVER` is unset) |
| `MCP_REGISTRY_PROJECT_ID` | `$PROJECT_ID` | GCP project hosting the Agent Registry |
| `MCP_REGISTRY_LOCATION` | `global` | Location of the Agent Registry resources |
| `MCP_REGISTRY_SERVER` | — | Full name of the registered MCP server (`projects/.../locations/.../mcpServers/...`); when set, agents connect via Agent Registry instead of the raw URL |
| `FINANCIAL_PLANNER_ENGINE` | `projects/PLACEHOLDER...` | ReasoningEngine resource name of the remote financial planner (Agent Runtime A2A) |
| `LOGS_BUCKET_NAME` | — | (optional) GCS bucket for prompt/response logging |

### Config var details

- **`GOOGLE_CLOUD_PROJECT`** — Your GCP project ID. Injected by the runtime when
  deployed; set it locally (or in `.env`) to match your project. Read at deploy
  time by `deploy_adk.py` and at call time by `app/tools/a2a_planner_tool.py`.

- **`GOOGLE_CLOUD_LOCATION`** — GCP region, e.g. `us-central1`. Used by the
  supervisor's A2A client, by `AdkApp`'s session and memory services, and by
  `vertexai.Client`. Note `MODEL_LOCATION` (below) is separate — it controls
  which Vertex endpoint the model calls route to, not where the agent runs.

- **`AGENT_MODEL`** — The Gemini model used by *every* agent (supervisor and
  sub-agents). Default `gemini-2.5-flash` (the cheapest Gemini text model).
  Read at call time by `app/config/models.py`, so you can change it via the
  deployment env vars without redeploying.

- **`MODEL_LOCATION`** — Vertex AI endpoint location for model calls. Default
  `global`, which spreads load across regions and avoids dynamic shared-quota
  throttling on regional endpoints. The engine instance still lives in its
  configured region; only model requests go global.

- **`MCP_PORTFOLIO_URL`** — URL of the MCP portfolio server used by the
  portfolio/trade/market-research/support agents via `ResilientMcpToolset`.
  Default `http://localhost:8080/mcp` for local dev. Used as a fallback when
  `MCP_REGISTRY_SERVER` is not set. The agents degrade gracefully (an
  informational tool) if the server is unreachable — they won't crash the turn.

- **`MCP_REGISTRY_SERVER`** (plus `MCP_REGISTRY_PROJECT_ID` /
  `MCP_REGISTRY_LOCATION`) — when set, the agents connect to the portfolio MCP
  server through the Google Cloud **Agent Registry** instead of the raw URL. The
  value is the full resource name of the registered MCP server, e.g.
  `projects/<project>/locations/<location>/mcpServers/mcp-portfolio`. The
  registry provides discovery and auth for the MCP endpoint. See
  `app/app_utils/api_registry_mcp.py`. The runtime service account needs
  `roles/agentregistry.viewer`.

- **`FINANCIAL_PLANNER_ENGINE`** — full ReasoningEngine resource name of the
  separately-deployed financial planner that the supervisor reaches through the
  `call_financial_planner` tool (`app/tools/a2a_planner_tool.py`). The planner
  runs on **Agent Runtime** as a native A2A agent:

  ```
  projects/<project>/locations/<region>/reasoningEngines/<id>
  ```

  Agent Runtime serves no public agent card (only an authenticated one at
  `{engine}/a2a/v1/card`), so the engine is addressed by resource name rather
  than by fetching a card. The tool calls the registered A2A operation
  `on_message_send` through the Agent Platform SDK, reusing one process-wide
  client. Each call uses a fresh message/task (stateless by design). The value
  is printed by the planner repo's `deploy.personal.a2a.sh` / `deploy.a2a.sh`.

- **`LOGS_BUCKET_NAME`** — (optional) GCS bucket for prompt/response logging.
  When set together with `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`,
  `setup_telemetry()` (`app/app_utils/telemetry.py`) enables GenAI
  prompt-response logging to `gs://<bucket>/completions`. Without it, logging
  falls back to Cloud Logging metadata only.

- **`GOOGLE_CLOUD_AGENT_ENGINE_ID`** — (advanced, runtime-injected) Set by the
  platform at deploy time. `AdkApp.set_up()` uses it (with
  `GOOGLE_CLOUD_AGENT_ENGINE_LOCATION`) to build the `VertexAiSessionService` and
  the `VertexAiMemoryBankService`, so sessions and memories persist across
  containers. You normally don't set this by hand.

- **`GOOGLE_CLOUD_AGENT_ENGINE_LOCATION`** — (advanced, runtime-injected)
  Region of the engine instance, used with the engine ID above. Not the same as
  `MODEL_LOCATION`.

- **Memory Bank** is selected from `GOOGLE_CLOUD_AGENT_ENGINE_ID`, so a deployed
  agent uses its runtime's Memory Bank automatically. Pointing at a *dedicated*
  Memory Bank instance instead means passing a `memory_service_builder` to
  `AdkApp` in `deploy_adk.py`. All agents (supervisor and sub-agents) use
  `preload_memory`/`load_memory` to recall memories, and
  `save_session_to_memory_callback` (`app/app_utils/memory_callbacks.py`)
  persists each session through the `after_agent_callback`, scoped by
  `app_name` + `user_id`.

## Deployment

The deploy is an SDK object deploy of `vertexai.agent_engines.AdkApp`: Agent
Runtime builds the container from the pickled agent plus the bundled `app`
package and a pinned requirements list. There is no Dockerfile and no Artifact
Registry repository involved. `AdkApp` also registers the engine's operations for
us — `:query`, `:streamQuery`, and the session/memory methods.

Run in Cloud Shell:

- `./build.sh` — installs `uv`, syncs dependencies, and runs the lint gate
  (`ruff format --check` + `ruff check`).
- `./deploy.sh` — sources `geap.deploy.env`, then `uv run python deploy_adk.py`.
- `./deploy.personal.sh` — the same, against `deploy.personal.env`.

Both deploy scripts pin the engine to a single replica (`min_instances=1`,
`max_instances=1`) so in-flight sessions see a stable process.

`STAGING_BUCKET` is required: Agent Runtime stages the pickle, the requirements
file and the `app` package there. It is a deploy-time variable only — it is not
passed to the runtime as an env var.

### Two environments, two self-contained env files

Each environment has its own complete env file — the same variables in both,
different values. Each deploy script sources **exactly one** of them:

| Script | Sources | Environment |
|---|---|---|
| `./deploy.sh` | `geap.deploy.env` | Office (default project `labs-gcp-msls-16495-1782829337`, `us-east1`) |
| `./deploy.personal.sh` | `deploy.personal.env` | Personal (`adk-tut-508714`, `us-central1`) |

Both files define the same variables (`PROJECT_ID`, `REGION`, `STAGING_BUCKET`,
`AGENT_MODEL`, `MODEL_LOCATION`, `MCP_PORTFOLIO_URL`, `MCP_REGISTRY_SERVER`,
`FINANCIAL_PLANNER_ENGINE`) — so picking which file a script sources is what
picks which environment it deploys to. To point an environment at a different
financial planner, edit **only** that environment's file:

```bash
# deploy.personal.env — the planner's Agent Runtime engine (A2A)
FINANCIAL_PLANNER_ENGINE=projects/adk-tut-508714/locations/us-central1/reasoningEngines/<id>
```

That single value is what the supervisor's `call_financial_planner` tool
(`app/tools/a2a_planner_tool.py`) reads at runtime.

- `geap.deploy.env` is committed to version control.
- `deploy.personal.env` is **gitignored** — copy it per-machine and fill in
  your own values.

Any value can still be overridden per-run: `PROJECT_ID=my-project ./deploy.sh`.
