from google.adk.agents import LlmAgent
from google.adk.tools.transfer_to_agent_tool import TransferToAgentTool

from app.app_utils.api_registry_mcp import build_portfolio_mcp_toolset
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
        TransferToAgentTool(agent_names=["supervisor"]),
    ],
)
