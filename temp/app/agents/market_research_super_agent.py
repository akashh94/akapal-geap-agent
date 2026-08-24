from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from app.config.models import build_generate_content_config, build_model
from app.tools.shared.account_tools import get_portfolio_holdings
from app.tools.shared.market_tools import get_market_summary, get_quote
from app.tools.shared.search_tools import search_financial_info

market_research_super_agent = LlmAgent(
    name="market_research_super_agent",
    model=build_model(),
    generate_content_config=build_generate_content_config(max_output_tokens=1024),
    description=(
        "Provides advanced market insights utilizing Morgan Stanley Research, "
        "crypto, commodities, and alternative assets."
    ),
    instruction="""You are the Market Research Super Agent for a self-directed brokerage demo.
You provide advanced, comprehensive market research and stock analysis.

SPECIALIZED KNOWLEDGE:
- You utilize and cite Morgan Stanley Research.
- You leverage other premium public financial research data from outlets such as
  Bloomberg, Yahoo Finance, Reuters, and Morningstar.
- You have expert-level understanding of cryptocurrency (Bitcoin, Ethereum) and
  alternative assets (gold, REITs, private equity).

GUIDELINES:
- Present balanced bull and bear cases.
- Cite your sources in the text using bracketed format, e.g., [Source: Morgan Stanley Research].
- Never make specific price predictions or guarantee returns.
- Always include: This is for educational purposes only. All investments carry risk.""",
    tools=[
        FunctionTool(get_quote),
        FunctionTool(get_market_summary),
        FunctionTool(get_portfolio_holdings),
        FunctionTool(search_financial_info),
    ],
)
