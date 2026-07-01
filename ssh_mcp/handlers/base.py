"""Handler protocol and optional base class."""

from __future__ import annotations

from typing import Awaitable, Callable, Protocol

from mcp.types import TextContent

from .context import HandlerContext


Handler = Callable[[HandlerContext, dict], Awaitable[list[TextContent]]]


class HandlerProtocol(Protocol):
    """Protocol for tool handler callables."""

    async def __call__(self, ctx: HandlerContext, args: dict) -> list[TextContent]:
        ...
