from google.adk.agents import LlmAgent
from google.adk.tools import load_memory, preload_memory

from app.agents.market_research_agent import market_research_agent
from app.agents.mortgage_agent import mortgage_agent
from app.agents.portfolio_agent import portfolio_agent
from app.agents.support_agent import support_agent
from app.agents.trade_agent import trade_agent
from app.app_utils.memory_callbacks import save_session_to_memory_callback
from app.config.models import build_model
from app.prompts.supervisor_prompt import SUPERVISOR_PROMPT
from app.tools.a2a_planner_tool import financial_planner_tool

root_agent = LlmAgent(
    name="supervisor",
    model=build_model(),
    instruction=SUPERVISOR_PROMPT,
    sub_agents=[
        portfolio_agent,
        trade_agent,
        market_research_agent,
        support_agent,
        mortgage_agent,
    ],
    tools=[
        financial_planner_tool,
        preload_memory,
        load_memory,
    ],
    after_agent_callback=save_session_to_memory_callback,
)
