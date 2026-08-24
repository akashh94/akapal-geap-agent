from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from app.config.models import build_generate_content_config, build_model
from app.prompts.portfolio_prompt import PORTFOLIO_PROMPT
from app.tools.shared.account_tools import (
    get_account_summary,
    get_portfolio_holdings,
    get_sector_allocation,
)
from app.tools.shared.search_tools import search_financial_info

portfolio_analyst = LlmAgent(
    name="portfolio_analyst",
    model=build_model(),
    generate_content_config=build_generate_content_config(max_output_tokens=1024),
    description=(
        "Analyzes portfolio allocation, diversification, "
        "holdings, performance and sector exposure."
    ),
    instruction=PORTFOLIO_PROMPT,
    tools=[
        FunctionTool(get_portfolio_holdings),
        FunctionTool(get_account_summary),
        FunctionTool(get_sector_allocation),
        FunctionTool(search_financial_info),
    ],
)
