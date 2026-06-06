"""
Executor agent for the autonomous agent system.
Performs tool execution only - NO reasoning.
"""

from typing import Dict, Any
import time
from ..core.types import Node, ExecutionResult, ToolCall
from ..tools.registry import TOOL_REGISTRY
from ..utils.observability import log_tool_call, tracer


class ExecutorAgent:
    """
    Executor agent that executes tool calls exactly as specified.
    NO reasoning, NO fallback guessing, NO silent fixes.
    Strict execution only.
    """
    
    def __init__(self):
        """Initialize the executor agent."""
        pass
    
    async def execute(self, node: Node) -> ExecutionResult:
        """
        Execute a node's tool call.
        
        Args:
            node: The node to execute
            
        Returns:
            Execution result
        """
        if not node.tool_call:
            return ExecutionResult(
                node_id=node.id,
                success=False,
                error="Node has no tool call to execute"
            )
        
        tool_call = node.tool_call
        start_time = time.time()

        # Log tool execution start
        tracer.add_step("Executor", f"Running tool: {tool_call.tool_name}", {"node_id": node.id, "parameters": tool_call.parameters})

        try:
            # Execute the tool
            result = await TOOL_REGISTRY.execute_tool(
                tool_call.tool_name,
                **tool_call.parameters
            )

            duration_ms = (time.time() - start_time) * 1000

            # Log successful tool call
            log_tool_call(tool_call.tool_name, tool_call.parameters, success=True)
            tracer.add_step("Executor", f"Tool {tool_call.tool_name} completed", {"duration_ms": duration_ms})

            return ExecutionResult(
                node_id=node.id,
                success=True,
                result=result,
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Log failed tool call
            log_tool_call(tool_call.tool_name, tool_call.parameters, success=False)
            tracer.add_step("Executor", f"Tool {tool_call.tool_name} failed", {"error": str(e)})

            return ExecutionResult(
                node_id=node.id,
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )
    
    async def execute_tool_call(self, tool_call: ToolCall) -> Any:
        """
        Execute a tool call directly.
        
        Args:
            tool_call: The tool call to execute
            
        Returns:
            Tool execution result
        """
        return await TOOL_REGISTRY.execute_tool(
            tool_call.tool_name,
            **tool_call.parameters
        )