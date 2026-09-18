"""Deploy the supervisor as an ADK agent on Agent Runtime.

Object deploy of an ``agentplatform.agent_engines.AdkApp``: the platform serves
the ADK operations (``:query`` / ``:streamQuery``) against the agent, so there is
no FastAPI app, no uvicorn and no Dockerfile to own. ``agent_framework`` is
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

import agentplatform
from agentplatform.agent_engines import AdkApp
from google.genai import errors as genai_errors
from google.genai import types

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
    "google-genai==2.17.0",
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

client = agentplatform.Client(
    project=PROJECT_ID,
    location=REGION,
    http_options=types.HttpOptions(api_version="v1beta1"),
)

DISPLAY_NAME = "akapal-geap-agents"

CONFIG = {
    "display_name": DISPLAY_NAME,
    "description": (
        "Multi-agent brokerage supervisor, served as an ADK agent on Agent Runtime."
    ),
    "requirements": REQUIREMENTS,
    "extra_packages": EXTRA_PACKAGES,
    "staging_bucket": STAGING_BUCKET,
    "env_vars": ENV_VARS,
    "min_instances": 1,
    "max_instances": 1,
}

# Update the existing engine instead of creating another one, so the resource
# name clients hold in GEAP_ENGINE_ID stays valid across deploys.
matches = [
    engine.api_resource.name
    for engine in client.agent_engines.list(
        config={"filter": f'display_name="{DISPLAY_NAME}"'}
    )
]

if len(matches) > 1:
    raise SystemExit(
        f"{len(matches)} engines named {DISPLAY_NAME!r} already exist:\n  "
        + "\n  ".join(matches)
        + "\n\nDelete the superseded ones and re-run, so this deploy updates a "
        "single engine rather than one clients may not be calling."
    )

app = AdkApp(agent=root_agent)

if matches:
    try:
        remote = client.agent_engines.update(name=matches[0], agent=app, config=CONFIG)
        action = "Updated"
    except genai_errors.ClientError as exc:
        # An engine deployed from source files (spec.source_code_spec, e.g. by
        # agents-cli) cannot be converted to an object deploy in place -- the
        # API rejects the PATCH. Create the object-deployed replacement instead;
        # the old engine keeps running until it is deleted, so verify the new
        # one first.
        if "deployment_source" not in str(exc):
            raise
        print(
            f"\n{matches[0]} was deployed from source files and cannot be "
            "updated into an object deploy. Creating a new engine instead.\n"
            "Delete the old engine once the new one is verified.\n"
        )
        remote = client.agent_engines.create(agent=app, config=CONFIG)
        action = "Created (replacing an un-updatable engine)"
else:
    remote = client.agent_engines.create(agent=app, config=CONFIG)
    action = "Created"

resource_name = remote.api_resource.name
base = f"https://{REGION}-aiplatform.googleapis.com/v1/{resource_name}"

print(f"{action} engine : {resource_name}")
print(f":query        POST {base}:query")
print(f":streamQuery  POST {base}:streamQuery")
print("\nGEAP_ENGINE_ID keeps this value across deploys.")
