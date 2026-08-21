from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, load_memory, preload_memory
from google.adk.tools.load_web_page import load_web_page

from app.app_utils.api_registry_mcp import build_portfolio_mcp_toolset
from app.app_utils.memory_callbacks import save_session_to_memory_callback
from app.config.models import build_model
from app.prompts.trade_prompt import TRADE_PROMPT
from app.tools.google_search_tool import google_search_tool

_trade_mcp = build_portfolio_mcp_toolset()

trade_agent = LlmAgent(
    name="trade_assistant",
    model=build_model(),
    description="Explains order types, quotes, position sizing, and trading risks.",
    instruction=TRADE_PROMPT,
    tools=[
        _trade_mcp,
        google_search_tool,
        FunctionTool(load_web_page),
        preload_memory,
        load_memory,
    ],
    after_agent_callback=save_session_to_memory_callback,
)
