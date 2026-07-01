"""Shared execution context passed to every tool handler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HandlerContext:
    """Container for dependencies shared across tool handlers."""

    session_manager: Any
    key_manager: Any
    config_manager: Any
    env_config: dict
    logger: Any
    audit: Any | None
    tunnels: dict[int, "Tunnel"]
