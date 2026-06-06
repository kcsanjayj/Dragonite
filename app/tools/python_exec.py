"""
Python execution tool for the autonomous agent system.
Provides isolated Python code execution via subprocess sandbox.
"""

from typing import Dict, Any
from .registry import Tool
from ..utils.sandbox import sandbox


class PythonExecTool(Tool):
    """Python code execution tool with subprocess isolation."""

    def __init__(self):
        """Initialize the Python execution tool."""
        super().__init__(
            name="python_exec",
            description="Execute Python code in isolated sandbox and return the result"
        )

    async def execute(self, code: str, timeout: int = 30, **kwargs) -> Dict[str, Any]:
        """
        Execute Python code in isolated subprocess sandbox.

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds (OS-level enforced)
            **kwargs: Additional parameters

        Returns:
            Execution result
        """
        # Execute in subprocess sandbox with strict isolation
        sandbox_result = await sandbox.execute_python(code, timeout=timeout)

        return {
            "result": sandbox_result.result if sandbox_result.success else None,
            "stdout": sandbox_result.result if sandbox_result.success else "",
            "error": sandbox_result.error,
            "success": sandbox_result.success,
            "duration_ms": sandbox_result.duration_ms,
            "exit_code": sandbox_result.exit_code
        }

    def get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool's parameters."""
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds",
                    "default": 30
                }
            },
            "required": ["code"]
        }


def exec(code: str, namespace: Dict[str, Any]) -> Any:
    """Execute code in a namespace (synchronous wrapper)."""
    return eval(code, namespace)