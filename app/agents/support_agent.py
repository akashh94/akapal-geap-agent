import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import SseConnectionParams

from app.app_utils.resilient_mcp import ResilientMcpToolset
from app.config.models import build_model
from app.prompts.support_prompt import SUPPORT_PROMPT
from app.tools.google_search_tool import google_search_tool

_support_mcp = ResilientMcpToolset(
    connection_params=SseConnectionParams(
        url=os.getenv("MCP_PORTFOLIO_URL", "http://localhost:8001/sse"),
        timeout=10.0,
    ),
)

support_agent = LlmAgent(
    name="customer_support",
    model=build_model(),
    description="Answers platform, account, fee, document, and support questions.",
    instruction=SUPPORT_PROMPT,
    tools=[
        _support_mcp,
        google_search_tool,
    ],
)
