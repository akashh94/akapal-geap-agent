"""A2A tool that delegates financial-planning questions to the remote planner.

The planner runs on Agent Runtime as a native A2A agent, so this goes through
the Agent Platform SDK rather than a card fetch + JSON-RPC round trip: Agent
Runtime serves no public agent card (only an authenticated one at
``{engine}/a2a/v1/card``), and its A2A surface is the registered operation
``on_message_send``.

The planner is addressed by its full ReasoningEngine resource name
(``FINANCIAL_PLANNER_ENGINE``). The SDK rewrites the card's interface URL from
that resource name before connecting, so no URL plumbing is needed here.

The planner is stateless by design: each call gets a fresh message/task, so
follow-up planning questions are independent of one another.
"""

from __future__ import annotations

import functools
import logging
import os
import uuid

import vertexai
from a2a.types import Message, Part, Role, SendMessageRequest
from google.adk.tools import FunctionTool
from google.genai import types

# Full ReasoningEngine resource name of the planner, injected at deploy time:
#   projects/<project>/locations/<region>/reasoningEngines/<id>
# The placeholder fails loudly on first use until the value is set.
DEFAULT_PLANNER_ENGINE = (
    "projects/PLACEHOLDER/locations/us-central1/reasoningEngines/PLACEHOLDER"
)

# The planner runs a whole LLM turn behind the portfolio MCP server, which the
# client's default timeout is too short for. HttpOptions.timeout is in
# milliseconds.
_PLANNER_TIMEOUT_MS = 180_000


def _planner_engine() -> str:
    """Full ReasoningEngine resource name of the planner."""
    return os.environ.get("FINANCIAL_PLANNER_ENGINE", DEFAULT_PLANNER_ENGINE).strip()


@functools.cache
def _client() -> vertexai.Client:
    """Process-wide Agent Platform client, reused across planner calls.

    Building a cloud client is expensive (auth, TLS), so one instance serves
    every call.
    """
    return vertexai.Client(
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        # Runtime-injected agent-engine region first: GOOGLE_CLOUD_LOCATION is
        # not necessarily the engine's region (AdkApp resolves its own services
        # the same way).
        location=(
            os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION")
            or os.environ.get("GOOGLE_CLOUD_LOCATION")
            or "us-central1"
        ),
        http_options=types.HttpOptions(
            api_version="v1beta1", timeout=_PLANNER_TIMEOUT_MS
        ),
    )


def _extract_text(chunks: list) -> str:
    """Pull the answer text out of the A2A chunks the planner streams back."""
    texts: list[str] = []
    for chunk in chunks:
        task = getattr(chunk, "task", None)
        if task is not None:
            for message in task.history:
                if message.role == Role.ROLE_USER:
                    continue
                texts.extend(part.text for part in message.parts if part.text)
        update = getattr(chunk, "artifact_update", None)
        if update is not None:
            texts.extend(part.text for part in update.artifact.parts if part.text)
    return "\n".join(texts).strip()


async def call_financial_planner(request: str) -> str:
    """Delegate a financial-planning question to the remote planner agent.

    Args:
        request: The user's financial-planning question.

    Returns:
        The planner's text response, or an error message if it cannot answer.
    """
    try:
        remote = _client().agent_engines.get(name=_planner_engine())
        chunks = await remote.on_message_send(
            request=SendMessageRequest(
                message=Message(
                    message_id=f"supervisor-{uuid.uuid4()}",
                    role=Role.ROLE_USER,
                    parts=[Part(text=request)],
                )
            )
        )
        return _extract_text(chunks) or "The financial planner returned no answer."
    except Exception as exc:  # noqa: BLE001 - surface a helpful error to the LLM
        logging.warning("call_financial_planner failed: %s", exc, exc_info=True)
        return f"The financial planner could not answer: {exc}"


financial_planner_tool = FunctionTool(call_financial_planner)
