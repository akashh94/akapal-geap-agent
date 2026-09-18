"""Deploy the supervisor as an ADK agent on Agent Runtime.

Object deploy of a ``vertexai.agent_engines.AdkApp``: the platform serves the ADK
operations (``:query`` / ``:streamQuery``) against the agent, so there is no
FastAPI app, no uvicorn and no Dockerfile to own. ``agent_framework`` is
auto-detected as ``google-adk`` from the object, and ``AdkApp.set_up()`` picks
Vertex AI sessions and Memory Bank once the runtime injects
``GOOGLE_CLOUD_AGENT_ENGINE_ID``.

Run via ``deploy.sh`` (office) or ``deploy.personal.sh`` (personal), both of
which source the matching ``*.env`` file first.

Note: the deploy docs warn against passing GOOGLE_CLOUD_PROJECT,
GOOGLE_CLOUD_LOCATION, PORT or anything prefixed GOOGLE_CLOUD_AGENT_ENGINE as
env vars, so ENV_VARS below deliberately omits them.
"""

from __future__ import annotations

import os

import vertexai
from google.genai import types
from vertexai.agent_engines import AdkApp

from app.agent import root_agent

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
REGION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

# Required for the object deploy: Agent Runtime stages the pickled object, the
# requirements file and any dependency files under this bucket.
STAGING_BUCKET = os.environ["STAGING_BUCKET"]

ENV_VARS = {
    key: os.environ[key]
    for key in (
        "AGENT_MODEL",
        "MODEL_LOCATION",
        "MCP_PORTFOLIO_URL",
        "MCP_REGISTRY_PROJECT_ID",
        "MCP_REGISTRY_LOCATION",
        "MCP_REGISTRY_SERVER",
        "FINANCIAL_PLANNER_ENGINE",
        "LOGS_BUCKET_NAME",
    )
    if os.environ.get(key)
}

# Mirrors pyproject's runtime set, pinned to the versions this entrypoint is
# verified against. pydantic and cloudpickle are required by the SDK's
# object-deploy packaging.
REQUIREMENTS = [
    "google-adk[gcp,db,a2a,agent-identity]==2.6.2",
    "google-cloud-aiplatform[agent_engines,adk]==1.163.0",
    "google-cloud-firestore",
    "google-genai==2.16.0",
    "python-dotenv",
    "a2a-sdk==1.1.2",
    "fastapi",
    "uvicorn[standard]",
    "sse-starlette",
    "mcp>=1.24,<2",
    "beautifulsoup4",
    "lxml",
    "yfinance",
    "pydantic",
    "cloudpickle",
]

# The object deploy only ships the pickle and requirements by default, so the
# `app` package must be bundled explicitly - otherwise the pickled reference to
# `app.agent.root_agent` cannot be resolved and the container dies with
# "No module named 'app.agent'".
EXTRA_PACKAGES = ["app"]

client = vertexai.Client(
    project=PROJECT_ID,
    location=REGION,
    http_options=types.HttpOptions(api_version="v1beta1"),
)

remote = client.agent_engines.create(
    agent=AdkApp(agent=root_agent),
    config={
        "display_name": "akapal-geap-agents",
        "description": (
            "Multi-agent brokerage supervisor, served as an ADK agent on Agent Runtime."
        ),
        "requirements": REQUIREMENTS,
        "extra_packages": EXTRA_PACKAGES,
        "staging_bucket": STAGING_BUCKET,
        "env_vars": ENV_VARS,
        "min_instances": 1,
        "max_instances": 1,
    },
)

resource_name = remote.api_resource.name
base = f"https://{REGION}-aiplatform.googleapis.com/v1/{resource_name}"

print(f"Engine      : {resource_name}")
print(f":query       POST {base}:query")
print(f":streamQuery POST {base}:streamQuery")
print("\nPoint the client's GEAP_ENGINE_ID at the resource name above.")
