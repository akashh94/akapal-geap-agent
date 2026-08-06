import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import SseConnectionParams

from app.app_utils.resilient_mcp import ResilientMcpToolset
from app.config.models import build_model
from app.prompts.portfolio_prompt import PORTFOLIO_PROMPT

_portfolio_mcp = ResilientMcpToolset(
    connection_params=SseConnectionParams(
        url=os.getenv("MCP_PORTFOLIO_URL", "http://localhost:8080/sse"),
        timeout=10.0,
    ),
)

portfolio_agent = LlmAgent(
    name="portfolio_analyst",
    model=build_model(),
    description=(
        "Analyzes portfolio allocation, diversification, "
        "holdings, performance and sector exposure."
    ),
    instruction=PORTFOLIO_PROMPT,
    tools=[
        _portfolio_mcp,
    ],
)
