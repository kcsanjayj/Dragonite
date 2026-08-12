from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolDefinition:
    name: str
    description: str
    function: Callable[..., Any]


class ToolRegistry:
    """
    Central registry for tools available to the autonomous agent.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        function: Callable[..., Any],
    ) -> None:

        if name in self._tools:
            raise ValueError(
                f"Tool already registered: {name}"
            )

        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            function=function,
        )

    def get(
        self,
        name: str,
    ) -> ToolDefinition:

        if name not in self._tools:
            raise KeyError(
                f"Unknown tool: {name}"
            )

        return self._tools[name]

    def has(
        self,
        name: str,
    ) -> bool:

        return name in self._tools

    def list_tools(self) -> list[ToolDefinition]:

        return list(
            self._tools.values()
        )

    def execute(
        self,
        name: str,
        **kwargs: Any,
    ) -> Any:

        tool = self.get(name)

        return tool.function(
            **kwargs
        )