import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.load_web_page import load_web_page
from google.adk.tools.mcp_tool import SseConnectionParams

from app.app_utils.resilient_mcp import ResilientMcpToolset
from app.config.models import build_model
from app.prompts.market_research_prompt import MARKET_RESEARCH_PROMPT
from app.tools.google_search_tool import google_search_tool

_market_mcp = ResilientMcpToolset(
    connection_params=SseConnectionParams(
        url=os.getenv("MCP_PORTFOLIO_URL", "http://localhost:8001/sse"),
        timeout=10.0,
    ),
)

market_research_agent = LlmAgent(
    name="market_research",
    model=build_model(),
    description="Provides balanced stock analysis, market context, and investing education.",
    instruction=MARKET_RESEARCH_PROMPT,
    tools=[
        _market_mcp,
        google_search_tool,
        FunctionTool(load_web_page),
    ],
)
