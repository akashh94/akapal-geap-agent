from google.adk.agents import LlmAgent
from google.adk.tools import load_memory, preload_memory

from app.app_utils.api_registry_mcp import build_portfolio_mcp_toolset
from app.app_utils.memory_callbacks import save_session_to_memory_callback
from app.config.models import build_model
from app.prompts.portfolio_prompt import PORTFOLIO_PROMPT

_portfolio_mcp = build_portfolio_mcp_toolset()

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
        preload_memory,
        load_memory,
    ],
    after_agent_callback=save_session_to_memory_callback,
)
