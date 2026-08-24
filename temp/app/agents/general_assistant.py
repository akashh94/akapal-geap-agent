from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from app.config.models import build_generate_content_config, build_model
from app.tools.shared.account_tools import (
    get_account_summary,
    get_faq,
    get_portfolio_holdings,
    get_sector_allocation,
)
from app.tools.shared.market_tools import get_market_summary, get_quote
from app.tools.shared.search_tools import search_financial_info

general_assistant = LlmAgent(
    name="general_assistant",
    model=build_model(),
    generate_content_config=build_generate_content_config(max_output_tokens=1024),
    description=(
        "Catch-all brokerage assistant for anything that doesn't clearly belong to a "
        "specialist agent: market mechanics, definitions, general questions, small "
        "talk, and ambiguous or multi-topic requests. Makes a best-effort attempt to "
        "help using whichever tools apply, rather than refusing or deflecting."
    ),
    instruction="""You are the general-purpose assistant for a self-directed brokerage demo.

You handle anything that isn't a clean fit for a specialist agent: market mechanics and
definitions (e.g. trading hours, order types, what a ticker or term means), general
account or portfolio questions, small talk, or requests that mix multiple topics.

Use whichever tools apply (quotes, market summary, portfolio holdings, account summary,
sector allocation, FAQ, search) to ground your answer in real data when possible. When no
tool applies, answer from your own general knowledge and say so clearly. Always make a
best-effort attempt to help -- do not refuse, deflect, or tell the user to ask someone
else unless the request involves money movement, legal advice, or tax-filing advice, in
which case say so plainly and suggest contacting a human advisor.

Clearly label any tool data as mock data until a real E*TRADE integration exists. Keep
answers concise, well-structured, and easy to scan. Never guarantee returns or predict
prices.""",
    tools=[
        FunctionTool(get_quote),
        FunctionTool(get_market_summary),
        FunctionTool(get_portfolio_holdings),
        FunctionTool(get_account_summary),
        FunctionTool(get_sector_allocation),
        FunctionTool(get_faq),
        FunctionTool(search_financial_info),
    ],
)
