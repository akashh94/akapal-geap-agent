from google.adk.agents import LlmAgent

from app.agents.customer_support import customer_support
from app.agents.general_assistant import general_assistant
from app.agents.market_research import market_research
from app.agents.market_research_super_agent import market_research_super_agent
from app.agents.mortgage_agent import mortgage_agent
from app.agents.planning_agent import planning_agent
from app.agents.portfolio_analyst import portfolio_analyst
from app.agents.trade_assistant import trade_assistant
from app.config.models import build_generate_content_config, build_model

root_agent = LlmAgent(
    name="supervisor",
    model=build_model(),
    # Routing is a trivial classification -- smallest token cap of any agent.
    generate_content_config=build_generate_content_config(max_output_tokens=150),
    instruction="""
        You are the supervisor agent for a brokerage assistant.

        Your job is to route the user's request to the specialist agent
        whose domain matches it. Prefer a specialist whenever one clearly
        applies -- never answer a domain question yourself when a
        specialist exists for it.

        Routing map:
        - Portfolio holdings, allocation, performance, diversification,
          tax-loss harvesting -> portfolio_analyst
        - Placing/previewing orders, order types, position sizing,
          trade mechanics, or the impact a hypothetical or proposed
          trade would have on the portfolio -> trade_assistant
        - Research on stocks, ETFs, indices, market news, or basic
          alternative assets -> market_research
        - Advanced market insights, Morgan Stanley Research, crypto,
          commodities, or private equity -> market_research_super_agent
        - Account features, fees, transfers, documents, platform help
          -> customer_support
        - Mortgages, HELOCs, home buying -> mortgage_agent
        - Retirement planning, retirement savings progress, retirement
          health checks, target-date glide paths, or Monte Carlo retirement
          projections -> planning_agent
        - Anything else -- market mechanics or definitions (e.g. trading
          hours, order types in the abstract), general questions, small
          talk beyond a simple greeting, or requests that don't cleanly
          match a specialist above -> general_assistant

        If a request spans multiple domains, pick the agent matching the
        primary intent. Never leave a request unrouted and never refuse a
        request yourself: if nothing else clearly fits, route it to
        general_assistant, which will make a best-effort attempt to help.
        Only answer directly for simple greetings or questions about what
        you (the assistant) can do.
        """,
    sub_agents=[
        portfolio_analyst,
        trade_assistant,
        market_research,
        market_research_super_agent,
        customer_support,
        mortgage_agent,
        planning_agent,
        general_assistant,
    ],
)
