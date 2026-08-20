from google.adk.agents import LlmAgent

from app.app_utils.api_registry_mcp import build_portfolio_mcp_toolset
from app.config.models import build_model
from app.prompts.mortgage_prompt import MORTGAGE_PROMPT
from app.tools.google_search_tool import google_search_tool

_mortgage_mcp = build_portfolio_mcp_toolset()

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
