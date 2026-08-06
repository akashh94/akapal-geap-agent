import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import SseConnectionParams

from app.app_utils.resilient_mcp import ResilientMcpToolset
from app.config.models import build_model
from app.prompts.mortgage_prompt import MORTGAGE_PROMPT
from app.tools.google_search_tool import google_search_tool

_mortgage_mcp = ResilientMcpToolset(
    connection_params=SseConnectionParams(
        url=os.getenv("MCP_PORTFOLIO_URL", "http://localhost:8001/sse"),
        timeout=10.0,
    ),
)

mortgage_agent = LlmAgent(
    name="mortgage_agent",
    model=build_model(),
    description="Guides customers through mortgage and home-buying education.",
    instruction=MORTGAGE_PROMPT,
    tools=[
        _mortgage_mcp,
        google_search_tool,
    ],
)
