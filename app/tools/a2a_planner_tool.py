"""A2A tool that delegates financial-planning questions to the remote planner.

The supervisor (orchestrator) exposes a ``call_financial_planner``
``FunctionTool``. When invoked, it:

1. Fetches the deployed planner's A2A agent card (from the URL in
   ``FINANCIAL_PLANNER_URL``), authenticated with the ambient Google Cloud
   credentials.
2. Sends the user's question over A2A (JSON-RPC ``SendMessage``) using the
   a2a-sdk client and returns the planner's text answer.

The planner is stateless by design: each call gets a fresh task/session, so
follow-up planning questions are independent (no planner-side context is
carried between calls).

Deployment note (Model A / Cloud Run): the planner's FastAPI app serves its
own A2A routes and rewrites the card URL per-request to the public host, so
the card's advertised endpoint is already correct — no passthrough rewriting
is needed (unlike the old Agent Engine passthrough shape).
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

# The planner's A2A agent card. Override via FINANCIAL_PLANNER_URL at deploy
# time; the placeholder default fails loudly on first use until set. Expected
# format (Cloud Run / Model A):
#   https://<service>-<hash>.<region>.run.app/a2a/financial_planner/
#     .well-known/agent-card.json
DEFAULT_PLANNER_CARD_URL = (
    "https://PLACEHOLDER-FINANCIAL-PLANNER-BASE/a2a/financial_planner/"
    ".well-known/agent-card.json"
)


def _auth_headers() -> dict[str, str]:
    """Bearer token from ambient ADC, used for the planner's A2A endpoints."""
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


async def call_financial_planner(request: str) -> str:
    """Delegate a financial-planning question to the remote planner agent.

    Args:
        request: The user's financial-planning question.

    Returns:
        The planner's text response, or an error message if it cannot answer.
    """
    card_url = _planner_card_url()
    headers = _auth_headers()
    try:
        async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
            resp = await client.get(card_url)
            resp.raise_for_status()
            card = parse_agent_card(resp.json())

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


financial_planner_tool = FunctionTool(call_financial_planner)
