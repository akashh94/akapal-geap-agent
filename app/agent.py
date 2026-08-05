"""Single-file entry point for ADK web UI discovery.

``adk web`` uses ``is_single_agent_directory()`` to detect this file, then
``import app.agent`` and look for ``root_agent``.
"""

from app.agents.supervisor import root_agent

__all__ = ["root_agent"]
