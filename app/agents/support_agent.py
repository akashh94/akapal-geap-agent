from google.adk.agents import LlmAgent
from google.adk.tools import load_memory, preload_memory

from app.app_utils.api_registry_mcp import build_portfolio_mcp_toolset
from app.app_utils.memory_callbacks import save_session_to_memory_callback
from app.config.models import build_model
from app.prompts.support_prompt import SUPPORT_PROMPT
from app.tools.google_search_tool import google_search_tool

_support_mcp = build_portfolio_mcp_toolset()

support_agent = LlmAgent(
    name="customer_support",
    model=build_model(),
    description="Answers platform, account, fee, document, and support questions.",
    instruction=SUPPORT_PROMPT,
    tools=[
        _support_mcp,
        google_search_tool,
        preload_memory,
        load_memory,
    ],
    after_agent_callback=save_session_to_memory_callback,
)
