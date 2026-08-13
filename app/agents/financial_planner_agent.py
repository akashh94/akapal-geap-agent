"""Financial planner as an ADK ``RemoteA2aAgent`` sub-agent.

The planner is deployed to Vertex AI Agent Engine as an ``A2aAgent`` (Model B),
which serves the A2A protocol and hosts its agent card natively at the public
passthrough URL:

    https://<LOCATION>-aiplatform.googleapis.com/v1beta1/projects/<PROJECT_ID>/
      locations/<LOCATION>/reasoningEngines/<ENGINE_ID>/a2a

So the card's advertised interface URL is the correct public endpoint — no
URL rewriting is needed. ``RemoteA2aAgent`` is given the card URL and resolves
it lazily on first use (using the authenticated ``httpx_client``).

The planner is stateless by design: ``full_history_when_stateless=True`` keeps
follow-up planning questions independent (no planner-side context carried
between calls), matching the behavior of the former ``call_financial_planner``
tool.
"""

from __future__ import annotations

import functools
import os

import google.auth
import google.auth.transport.requests
import httpx
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# The planner's A2A agent card, hosted natively by Agent Engine at the A2A
# passthrough URL. Override via FINANCIAL_PLANNER_URL at deploy time; the
# placeholder default fails loudly on first use until set. Expected format:
#   https://<location>-aiplatform.googleapis.com/v1beta1/
#     projects/<project>/locations/<location>/reasoningEngines/<id>/a2a
#     /.well-known/agent-card.json
DEFAULT_PLANNER_CARD_URL = (
    "https://PLACEHOLDER-FINANCIAL-PLANNER-BASE/v1beta1/"
    "projects/PLACEHOLDER-PROJECT/locations/PLACEHOLDER-LOCATION/"
    "reasoningEngines/PLACEHOLDER-ENGINE-ID/a2a"
    "/.well-known/agent-card.json"
)

#: Timeout for the A2A JSON-RPC calls made by ``RemoteA2aAgent``.
_A2A_TIMEOUT_SECONDS = 180.0


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
    """The full agent-card URL from ``FINANCIAL_PLANNER_URL`` (cached)."""
    return os.getenv("FINANCIAL_PLANNER_URL", DEFAULT_PLANNER_CARD_URL).strip()


financial_planner = RemoteA2aAgent(
    name="financial_planner",
    description=(
        "Goals-based financial planning: retirement readiness, savings targets, "
        "cash-flow, and affordability projections."
    ),
    agent_card=_planner_card_url(),  # resolved lazily by RemoteA2aAgent
    httpx_client=httpx.AsyncClient(
        timeout=_A2A_TIMEOUT_SECONDS, headers=_auth_headers()
    ),
    full_history_when_stateless=True,
)
