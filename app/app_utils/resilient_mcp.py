"""Resilient MCP toolset that degrades gracefully when the MCP server is down.

Wraps :class:`google.adk.tools.mcp_tool.McpToolset` so a failure to reach the
MCP server (e.g. the portfolio service is not running) does not crash the
agent's turn. Instead, ``get_tools()`` returns a single informational
``FunctionTool`` that tells the model the portfolio data is unavailable, and a
cooldown prevents retrying the dead server on every turn.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import FunctionTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.mcp_tool import McpToolset

logger = logging.getLogger(__name__)

#: How long (seconds) to skip reconnecting after a failed connection attempt.
DEFAULT_COOLDOWN_SECONDS = 30.0

#: Name of the informational tool exposed while the MCP server is unreachable.
_UNAVAILABLE_TOOL_NAME = "portfolio_service_unavailable"


def _unavailable_tool(source: str) -> FunctionTool:
    """Build a no-op tool that reports the MCP server is unreachable."""

    def _check(src: str = source) -> str:
        return (
            "The portfolio data service is currently unavailable "
            f"(could not reach {src}). "
            "Do not invent portfolio numbers; tell the user the service is "
            "temporarily down and ask them to try again later."
        )

    _check.__name__ = _UNAVAILABLE_TOOL_NAME
    _check.__doc__ = (
        "Check the portfolio data service status. Call this when you need "
        "portfolio, quote, or market data and no live data source is "
        "available."
    )
    return FunctionTool(_check)


class ResilientMcpToolset(BaseToolset):
    """An ``McpToolset`` that degrades gracefully when the server is down.

    Wraps a lazily-created :class:`McpToolset` and adds connection resilience:

    * If ``get_tools()`` raises (the server is unreachable), the error is
      logged and an informational ``FunctionTool`` is returned instead, so the
      agent can keep answering (e.g. explain that portfolio data is
      unavailable).
    * A cooldown window (default 30s) prevents repeated connection attempts to
      a dead server across turns.
    """

    def __init__(
        self,
        *,
        connection_params=None,
        toolset_factory: Callable[[], BaseToolset] | None = None,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        **kwargs,
    ) -> None:
        super().__init__()
        if (connection_params is None) == (toolset_factory is None):
            raise ValueError(
                "Provide exactly one of connection_params or toolset_factory."
            )
        self._connection_params = connection_params
        self._toolset_factory = toolset_factory
        self._cooldown_seconds = cooldown_seconds
        self._kwargs = kwargs
        self._toolset: BaseToolset | None = None
        self._unavailable_since: float | None = None
        self._last_error: Exception | None = None

    def _get_toolset(self) -> BaseToolset:
        if self._toolset is None:
            if self._toolset_factory is not None:
                self._toolset = self._toolset_factory()
            else:
                self._toolset = McpToolset(
                    connection_params=self._connection_params, **self._kwargs
                )
        return self._toolset

    async def get_tools(
        self, readonly_context: ReadonlyContext | None = None
    ) -> list[FunctionTool]:
        now = time.monotonic()
        # If we're inside the cooldown window, don't attempt a reconnect.
        if (
            self._unavailable_since is not None
            and now - self._unavailable_since < self._cooldown_seconds
        ):
            logger.debug(
                "MCP server still in cooldown (%ss left); serving unavailable tool",
                round(self._cooldown_seconds - (now - self._unavailable_since), 1),
            )
            return [self._unavailable()]

        try:
            tools = await self._get_toolset().get_tools(readonly_context)
        except Exception as exc:  # noqa: BLE001 - any failure => degrade gracefully
            logger.warning(
                "MCP server unreachable (%s); serving unavailable tool for %ss",
                exc,
                self._cooldown_seconds,
            )
            self._unavailable_since = now
            self._last_error = exc
            return [self._unavailable()]
        else:
            # Success resets the failure state so the next failure gets a full
            # cooldown window.
            self._unavailable_since = None
            self._last_error = None
            return tools

    def _unavailable(self) -> FunctionTool:
        if self._connection_params is not None:
            source = getattr(
                self._connection_params, "url", str(self._connection_params)
            )
        else:
            source = "MCP server"
        return _unavailable_tool(source)

    async def close(self) -> None:
        """Release the underlying MCP session, if one was created."""
        if self._toolset is not None:
            await self._toolset.close()
