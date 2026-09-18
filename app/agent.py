"""Single-file entry point for ADK web UI discovery.

``adk web`` uses ``is_single_agent_directory()`` to detect this file, then
``import app.agent`` and look for ``root_agent``.

AdkApp resolves ``root_agent`` from here at runtime too, which is why the
process-wide setup (dotenv, telemetry) runs at import.
"""

from dotenv import load_dotenv

from app.agents.supervisor import root_agent
from app.app_utils.telemetry import setup_telemetry

load_dotenv()
setup_telemetry()

__all__ = ["root_agent"]
