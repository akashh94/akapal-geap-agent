from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from app.config.models import build_generate_content_config, build_model
from app.tools.shared.account_tools import get_portfolio_holdings
from app.tools.shared.market_tools import get_market_summary, get_quote
from app.tools.shared.search_tools import search_financial_info

market_research = LlmAgent(
    name="market_research",
    model=build_model(),
    generate_content_config=build_generate_content_config(max_output_tokens=1024),
    description=(
        "Researches stocks, ETFs, market indices, and alternative assets "
        "(crypto, commodities, REITs): balanced analysis, market context, "
        "and investing education."
    ),
    instruction="""You are the Market Research Agent for a self-directed brokerage demo.
You cover equities, ETFs, and market indices as well as alternative assets such as
crypto, commodities, and REITs. Use tools for current mock quotes, market data, or
portfolio context; do not claim access to premium research sources unless a real
integration is added. Explain jargon, present balanced bull and bear cases, and never
predict prices or guarantee returns. Relate analysis to a held position when relevant.
Clearly label tool data as mock data until an E*TRADE integration exists. Always
include: This is for educational purposes only. All investments carry risk.""",
    tools=[
        FunctionTool(get_quote),
        FunctionTool(get_market_summary),
        FunctionTool(get_portfolio_holdings),
        FunctionTool(search_financial_info),
    ],
)
