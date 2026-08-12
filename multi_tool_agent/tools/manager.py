from __future__ import annotations

from typing import Any

from .builtins import register_builtin_tools
from .executor import ToolExecutor
from .tool_registry import ToolRegistry


class ToolManager:
    """
    High-level tool layer used by the autonomous engine.

    Responsibilities:

    1. Create the registry.
    2. Register built-in tools.
    3. Execute tools.
    4. Provide tool descriptions to the planner.
    """

    def __init__(self) -> None:

        self.registry = ToolRegistry()

        register_builtin_tools(
            self.registry
        )

        self.executor = ToolExecutor(
            self.registry
        )

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        return self.executor.execute(
            tool_name,
            arguments,
        )

    def list_tools(self) -> list[dict[str, str]]:

        return [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in self.registry.list_tools()
        ]

    def has_tool(
        self,
        tool_name: str,
    ) -> bool:

        return self.registry.has(
            tool_name
        )