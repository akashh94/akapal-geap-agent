"""Shared Google Search tool wrapper for all agents.

Creates a single GoogleSearchAgentTool instance that agents import
instead of each constructing their own copy.
"""

from google.adk.tools.google_search_agent_tool import (
    GoogleSearchAgentTool,
    create_google_search_agent,
)

from app.config.models import build_model

google_search_tool = GoogleSearchAgentTool(create_google_search_agent(build_model()))
