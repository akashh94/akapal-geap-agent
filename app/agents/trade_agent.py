import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.load_web_page import load_web_page
from google.adk.tools.mcp_tool import SseConnectionParams

from app.app_utils.resilient_mcp import ResilientMcpToolset
from app.config.models import build_model
from app.prompts.trade_prompt import TRADE_PROMPT
from app.tools.google_search_tool import google_search_tool

_trade_mcp = ResilientMcpToolset(
    connection_params=SseConnectionParams(
        url=os.getenv("MCP_PORTFOLIO_URL", "http://localhost:8001/sse"),
        timeout=10.0,
    ),
)

trade_agent = LlmAgent(
    name="trade_assistant",
    model=build_model(),
    description="Explains order types, quotes, position sizing, and trading risks.",
    instruction=TRADE_PROMPT,
    tools=[
        _trade_mcp,
        google_search_tool,
        FunctionTool(load_web_page),
    ],
)
