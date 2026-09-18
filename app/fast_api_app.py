import logging
import os

import google.auth
from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging

# Imported for its side effect: `services` registers the shared:// factories in
# ADK's service registry.
from app.app_utils import services  # noqa: F401
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

# The agents directory that ADK scans for agent definitions. This is the app/
# package itself.
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    allow_origins=allow_origin,
    auto_create_session=True,
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
