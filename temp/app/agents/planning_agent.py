from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from app.config.models import build_generate_content_config, build_model
from app.prompts.planning_prompt import PLANNING_PROMPT
from app.tools.planning.retirement_tools import (
    get_glide_path_allocation,
    get_retirement_summary,
    render_retirement_dashboard,
    run_monte_carlo_projection,
)
from app.tools.shared.search_tools import search_financial_info

planning_agent = LlmAgent(
    name="planning_agent",
    model=build_model(model_env_var="PLANNING_AGENT_MODEL"),
    generate_content_config=build_generate_content_config(max_output_tokens=1024),
    description=(
        "Explains retirement planning: target-date progress, Monte Carlo "
        "success projections, and glide-path asset allocation. Renders the "
        "interactive A2UI retirement dashboard for health-check requests."
    ),
    instruction=PLANNING_PROMPT,
    tools=[
        FunctionTool(get_retirement_summary),
        FunctionTool(run_monte_carlo_projection),
        FunctionTool(get_glide_path_allocation),
        FunctionTool(render_retirement_dashboard),
        FunctionTool(search_financial_info),
    ],
)
