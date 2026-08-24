"""Shared model configuration for all GEAP agents."""

import os

from google.adk.models.google_llm import Gemini
from google.genai import types

DEFAULT_MODEL = "gemini-3.5-flash"

# POC projects have low default Vertex AI requests-per-minute quota, and a
# multi-agent turn fires several model calls in quick succession — 429
# RESOURCE_EXHAUSTED bursts are expected. Retry with exponential backoff
# instead of failing the turn.
_RETRY_OPTIONS = types.HttpRetryOptions(
    attempts=6,
    initial_delay=2.0,
    exp_base=2.0,
    http_status_codes=[429, 500, 503, 504],
)


def build_model(
    *, model_env_var: str | None = None, default_model: str = DEFAULT_MODEL
) -> Gemini:
    """Return the Gemini model used by a GEAP agent.

    Reads MODEL_LOCATION from the environment at call time, so the deployed
    engine picks up values set via .env or the deployment environment (e.g.
    Cloud Run / Agent Engine env vars). Model name resolution, most specific
    wins:

    1. ``default_model`` (this function's default: DEFAULT_MODEL)
    2. ``AGENT_MODEL`` env var, if set -- overrides every agent at once
    3. ``model_env_var`` (e.g. "PLANNING_AGENT_MODEL"), if given and set --
       overrides just the one agent that passed it, even over AGENT_MODEL

    Model calls route to the "global" endpoint by default: regional
    endpoints run on dynamic shared quota and throttle bursts even when
    single calls succeed, while global spreads load across regions. The
    Agent Engine instance itself still lives in its configured region —
    only the model requests go global.
    """
    model_name = default_model
    if os.getenv("AGENT_MODEL"):
        model_name = os.getenv("AGENT_MODEL")
    if model_env_var and os.getenv(model_env_var):
        model_name = os.getenv(model_env_var)

    return Gemini(
        model=model_name,
        retry_options=_RETRY_OPTIONS,
        client_kwargs={
            "vertexai": True,
            "location": os.getenv("MODEL_LOCATION", "global"),
        },
    )


def build_generate_content_config(
    max_output_tokens: int,
) -> types.GenerateContentConfig:
    """Aggressive, demo-tuned generation config: minimal thinking plus a hard
    output-token ceiling, applied to every agent (including the supervisor's
    trivial routing decision) so no hop pays for reasoning depth it doesn't
    need.

    NOTE: this trades answer quality/completeness for latency -- minimal
    thinking means less multi-step reasoning before answering, and the token
    cap can truncate a long answer mid-sentence. That's an acceptable
    trade-off for a fast demo; revisit both before any production use.
    """
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.MINIMAL,
        ),
        max_output_tokens=max_output_tokens,
    )
