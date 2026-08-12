from __future__ import annotations

from typing import Any

from .tool_registry import ToolRegistry


class ToolExecutor:
    """
    Executes tools registered in ToolRegistry.

    This is the bridge between the autonomous DAG
    and actual external/local capabilities.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        arguments = arguments or {}

        print(
            f"[Tool Executor] Calling: {tool_name}"
        )

        if not self.registry.has(tool_name):
            error = f"Unknown tool: {tool_name}"

            print(
                f"[Tool Executor] FAILED: {error}"
            )

            return {
                "success": False,
                "tool": tool_name,
                "result": None,
                "error": error,
            }

        try:
            result = self.registry.execute(
                tool_name,
                **arguments,
            )

            print(
                f"[Tool Executor] SUCCESS: {tool_name}"
            )

            return {
                "success": True,
                "tool": tool_name,
                "result": result,
                "error": None,
            }

        except Exception as exc:

            print(
                f"[Tool Executor] FAILED: {tool_name}"
            )

            print(
                f"[Tool Executor] Error: {exc}"
            )

            return {
                "success": False,
                "tool": tool_name,
                "result": None,
                "error": str(exc),
            }