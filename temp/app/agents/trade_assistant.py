from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from app.config.models import build_generate_content_config, build_model
from app.tools.shared.account_tools import get_account_summary, get_portfolio_holdings
from app.tools.shared.market_tools import get_market_summary, get_quote
from app.tools.shared.search_tools import search_financial_info
from app.tools.shared.ui_tools import show_rebalance_widget
from app.tools.trading.order_tools import preview_order_impact

trade_assistant = LlmAgent(
    name="trade_assistant",
    model=build_model(),
    generate_content_config=build_generate_content_config(max_output_tokens=1024),
    description="Explains order types, quotes, position sizing, and trading risks.",
    instruction="""You are the Trade Assistant Agent for a self-directed brokerage demo.
Use tools before discussing quotes or the user's portfolio. Explain market, limit,
stop, and stop-limit orders and their speed-versus-price tradeoff. Flag a proposed
position that would exceed 15% of portfolio value. Never guarantee returns or place
an order. Always end trade guidance with: This is for educational purposes only.
All investments carry risk. All tool data is mock data until an E*TRADE integration exists.

When you recommend a specific rebalance action (e.g. trimming a concentrated
position into a diversified asset), call show_rebalance_widget in addition to
your normal text explanation so the client can render an interactive ticket.""",
    tools=[
        FunctionTool(get_quote),
        FunctionTool(get_portfolio_holdings),
        FunctionTool(get_account_summary),
        FunctionTool(get_market_summary),
        FunctionTool(search_financial_info),
        FunctionTool(preview_order_impact),
        FunctionTool(show_rebalance_widget),
    ],
)
