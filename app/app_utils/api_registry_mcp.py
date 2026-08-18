"""Build a resilient MCP toolset for the portfolio data server.

Connects to the portfolio MCP server through the Google Cloud API Registry
when ``MCP_REGISTRY_SERVER`` is set, and falls back to a direct Streamable
HTTP connection (``MCP_PORTFOLIO_URL``) otherwise so local development keeps
working without a registry.

The returned :class:`ResilientMcpToolset` degrades gracefully when the MCP
server is unreachable (see ``app.app_utils.resilient_mcp``).
"""

from __future__ import annotations

import logging
import os

from google.adk.integrations.api_registry import ApiRegistry
from google.adk.tools.base_toolset import BaseToolset

from app.app_utils.resilient_mcp import ResilientMcpToolset

logger = logging.getLogger(__name__)

#: Default Streamable HTTP URL for local development (no registry).
_DEFAULT_LOCAL_MCP_URL = "http://localhost:8080/mcp"


def _build_registry_toolset() -> BaseToolset:
    """Build an ``McpToolset`` for the MCP server registered in API Registry.

    Reads the registry configuration from the environment:

    * ``MCP_REGISTRY_PROJECT_ID`` — project where the API Registry lives
      (defaults to ``GOOGLE_CLOUD_PROJECT`` if unset).
    * ``MCP_REGISTRY_LOCATION`` — location of the registry resource
      (defaults to ``global``).
    * ``MCP_REGISTRY_SERVER`` — full resource name of the registered MCP
      server, e.g.
      ``projects/<project>/locations/<location>/mcpServers/<name>``.
    """
    project_id = os.getenv(
        "MCP_REGISTRY_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "")
    )
    location = os.getenv("MCP_REGISTRY_LOCATION", "global")
    server_name = os.getenv("MCP_REGISTRY_SERVER", "")

    if not project_id or not server_name:
        raise ValueError(
            "MCP_REGISTRY_PROJECT_ID and MCP_REGISTRY_SERVER must be set "
            "when using the API Registry connection."
        )

    logger.info(
        "Connecting portfolio MCP via API Registry: project=%s location=%s server=%s",
        project_id,
        location,
        server_name,
    )
    api_registry = ApiRegistry(
        api_registry_project_id=project_id,
        location=location,
    )
    return api_registry.get_toolset(mcp_server_name=server_name)


def build_portfolio_mcp_toolset() -> ResilientMcpToolset:
    """Return a resilient toolset for the portfolio MCP server.

    Uses the API Registry connection when ``MCP_REGISTRY_SERVER`` is set;
    otherwise falls back to the direct SSE URL from ``MCP_PORTFOLIO_URL``.
    """
    if os.getenv("MCP_REGISTRY_SERVER"):
        return ResilientMcpToolset(toolset_factory=_build_registry_toolset)

    from google.adk.tools.mcp_tool import StreamableHTTPConnectionParams

    url = os.getenv("MCP_PORTFOLIO_URL", _DEFAULT_LOCAL_MCP_URL)
    logger.info("Connecting portfolio MCP via direct Streamable HTTP: %s", url)
    return ResilientMcpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=url,
            timeout=10.0,
        ),
    )
