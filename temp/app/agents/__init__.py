"""Sub-agent definitions — internal package, not a standalone ADK app."""

from app.agents.customer_support import customer_support
from app.agents.general_assistant import general_assistant
from app.agents.market_research import market_research
from app.agents.market_research_super_agent import market_research_super_agent
from app.agents.mortgage_agent import mortgage_agent
from app.agents.portfolio_analyst import portfolio_analyst
from app.agents.trade_assistant import trade_assistant

__all__ = [
    "customer_support",
    "general_assistant",
    "market_research",
    "market_research_super_agent",
    "mortgage_agent",
    "portfolio_analyst",
    "trade_assistant",
]
