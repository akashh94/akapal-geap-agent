"""A2A tool that delegates financial-planning questions to the remote planner.

The supervisor (orchestrator) exposes a single ``call_financial_planner``
``FunctionTool``. When invoked, it:

1. Fetches the deployed planner's A2A agent card (from the Agent Engine HTTP
   passthrough URL in ``FINANCIAL_PLANNER_URL``), authenticated with the
   ambient Google Cloud credentials.
2. Rewrites the card's advertised endpoint to the public passthrough URL —
   the card advertises the container's internal URL, which is not reachable
   directly.
3. Sends the user's question over A2A (JSON-RPC ``SendMessage``) using the
   a2a-sdk client and returns the planner's text answer.

The planner is stateless by design: each call gets a fresh task/session, so
follow-up planning questions are independent (no planner-side context is
carried between calls).
"""

from __future__ import annotations

import functools
import logging
import os
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.client.card_resolver import parse_agent_card
from a2a.types import Message, Part, Role, SendMessageRequest
from google.adk.tools import FunctionTool

# The planner's A2A agent card, served by Agent Engine's HTTP passthrough.
# Override via FINANCIAL_PLANNER_URL at deploy time; the placeholder default
# fails loudly on first use until set. Expected format:
#   https://<location>-aiplatform.googleapis.com/reasoningEngines/v1/
#     projects/<project>/locations/<location>/reasoningEngines/<id>/
#     api/a2a/<agent_directory>/.well-known/agent-card.json
DEFAULT_PLANNER_CARD_URL = (
    "https://PLACEHOLDER-FINANCIAL-PLANNER-BASE/reasoningEngines/v1/"
    "projects/PLACEHOLDER-PROJECT/locations/PLACEHOLDER-LOCATION/"
    "reasoningEngines/PLACEHOLDER-ENGINE-ID/api/a2a/app/"
    ".well-known/agent-card.json"
)

_USER_ID = "geap-orchestrator"


def _auth_headers() -> dict[str, str]:
    """Bearer token from ambient ADC, used for the Agent Engine passthrough."""
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }


@functools.cache
def _planner_card_url() -> str:
    return os.getenv("FINANCIAL_PLANNER_URL", DEFAULT_PLANNER_CARD_URL).strip()


def _passthrough_base(card_url: str) -> str:
    """The JSON-RPC base URL, derived from the card URL (drop the card suffix).

    ``.../api/a2a/<dir>/.well-known/agent-card.json`` -> ``.../api/a2a/<dir>``
    """
    return card_url.rsplit("/.well-known/agent-card.json", 1)[0]


async def call_financial_planner(request: str) -> str:
    """Delegate a financial-planning question to the remote planner agent.

    Args:
        request: The user's financial-planning question.

    Returns:
        The planner's text response, or an error message if it cannot answer.
    """
    card_url = _planner_card_url()
    rpc_base = _passthrough_base(card_url)
    headers = _auth_headers()
    try:
        async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
            resp = await client.get(card_url)
            resp.raise_for_status()
            card = parse_agent_card(resp.json())
        # The card advertises the container's internal URL; use the public
        # passthrough URL instead.
        for interface in card.supported_interfaces:
            interface.url = rpc_base

        factory = ClientFactory(
            ClientConfig(
                supported_protocol_bindings=["JSONRPC"],
                use_client_preference=True,
                httpx_client=httpx.AsyncClient(timeout=180.0, headers=headers),
            )
        )
        a2a_client = factory.create(card)
        message = Message(
            message_id=f"supervisor-{uuid.uuid4()}",
            role=Role.ROLE_USER,
            parts=[Part(text=request)],
        )
        texts: list[str] = []
        async for chunk in a2a_client.send_message(SendMessageRequest(message=message)):
            # chunk is a protobuf message; collect text from artifact parts.
            artifact_update = getattr(chunk, "artifact_update", None)
            if artifact_update is not None:
                for part in artifact_update.artifact.parts:
                    if part.text:
                        texts.append(part.text)
            task = getattr(chunk, "task", None)
            if task is not None:
                for msg in task.history:
                    if msg.role == Role.ROLE_USER:
                        continue
                    for part in msg.parts:
                        if part.text:
                            texts.append(part.text)
        return "\n".join(texts).strip() or ("The financial planner returned no answer.")
    except Exception as exc:  # noqa: BLE001 - surface a helpful error to the LLM
        logging.warning("call_financial_planner failed: %s", exc, exc_info=True)
        return f"The financial planner could not answer: {exc}"


call_financial_planner = FunctionTool(call_financial_planner)
