import contextlib
import logging
import os
from collections.abc import AsyncIterator

import google.auth
from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.cloud import logging as google_cloud_logging

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

load_dotenv()
setup_telemetry()

logger = logging.getLogger(__name__)

try:
    _, project_id = google.auth.default()
except Exception:
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "unknown")

# get_fast_api_app wires a Vertex agent_engines.AdkApp when
# gemini_enterprise_app_name is set, which requires a project. Initialize
# vertexai so it resolves from the environment (service account on Agent
# Engine/Cloud Run, or GOOGLE_CLOUD_PROJECT locally).
if project_id and project_id != "unknown":
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
    try:
        import vertexai

        vertexai.init(project=project_id)
    except Exception as exc:
        logger.warning("vertexai.init() failed — proceeding without it (%s)", exc)
try:
    logging_client = google_cloud_logging.Client()
    logger = logging_client.logger(__name__)
except Exception as exc:
    logger.warning(
        "Cloud Logging unavailable — /feedback will fall back to console (%s)", exc
    )
allow_origin = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

# The agents directory that ADK scans for agent definitions (and, when a2a=True,
# for agent.json A2A cards). This is the app/ package itself.
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import root_agent

    runner = Runner(
        agent=root_agent,
        app_name=root_agent.name,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = root_agent.name
    # Register A2A (Agent2Agent) routes under /a2a/<app_name> sharing the same
    # runner, so A2A clients and Gemini Enterprise A2A can reach the agent.
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{root_agent.name}",
    )
    yield


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    allow_origins=allow_origin,
    auto_create_session=True,
    lifespan=lifespan,
    gemini_enterprise_app_name="app",
)
app.title = "geap-agents"
app.description = "API for interacting with the Agent geap-agents"


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    if isinstance(logger, google_cloud_logging.Logger):
        logger.log_struct(feedback.model_dump(), severity="INFO")
    else:
        logger.info("feedback: %s", feedback.model_dump())
    return {"status": "success"}
