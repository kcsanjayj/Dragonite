"""
Tool registry for the autonomous agent system.
Single source of truth for all available tools.
"""

from typing import Callable, Dict, Any, Optional
from abc import ABC, abstractmethod


class Tool(ABC):
    """Abstract base class for tools."""
    
    def __init__(self, name: str, description: str):
        """Initialize the tool."""
        self.name = name
        self.description = description
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool's parameters."""
        pass


class ToolRegistry:
    """
    Registry for managing tools.
    Single source of truth for all available tools.
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> None:
        """
        Unregister a tool.
        
        Args:
            name: Name of the tool to unregister
        """
        if name in self._tools:
            del self._tools[name]
    
    def get(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name.
        
        Args:
            name: Name of the tool
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)
    
    def list_tools(self) -> Dict[str, str]:
        """
        List all registered tools with their descriptions.
        
        Returns:
            Dictionary mapping tool names to descriptions
        """
        return {name: tool.description for name, tool in self._tools.items()}
    
    def get_all_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        Get schemas for all registered tools.
        
        Returns:
            Dictionary mapping tool names to their schemas
        """
        return {name: tool.get_schema() for name, tool in self._tools.items()}
    
    def _validate_params(self, tool: Tool, params: Dict[str, Any]) -> None:
        """
        Validate tool parameters against JSON schema.

        Args:
            tool: The tool to validate against
            params: Parameters to validate

        Raises:
            ValueError: If parameters are invalid
        """
        schema = tool.get_schema()
        if not schema:
            return  # No schema to validate against

        try:
            from jsonschema import validate, ValidationError
            validate(instance=params, schema=schema)
        except ValidationError as e:
            raise ValueError(f"Invalid parameters for tool '{tool.name}': {e.message}")
        except ImportError:
            # jsonschema not installed, skip validation with warning
            import warnings
            warnings.warn("jsonschema not installed, skipping parameter validation")

    async def execute_tool(self, name: str, use_cache: bool = True, use_circuit_breaker: bool = True, **kwargs) -> Any:
        """
        Execute a tool by name with schema validation, caching, and circuit breaker.

        Args:
            name: Name of the tool to execute
            use_cache: Whether to use caching (default True)
            use_circuit_breaker: Whether to use circuit breaker (default True)
            **kwargs: Parameters for the tool

        Returns:
            Result of tool execution

        Raises:
            ValueError: If tool not found or parameters invalid
            RuntimeError: If circuit breaker is open
        """
        from ..utils.cache import result_cache
        from ..utils.circuit_breaker import circuit_breakers

        tool = self.get(name)
        if tool is None:
            raise ValueError(f"Tool '{name}' not found")

        # Check circuit breaker
        if use_circuit_breaker:
            if not circuit_breakers.can_execute(name):
                stats = circuit_breakers.get_breaker(name).get_stats()
                raise RuntimeError(f"Circuit breaker open for tool '{name}': {stats}")

        # Validate parameters against schema before execution
        self._validate_params(tool, kwargs)

        # Check cache first
        if use_cache:
            cached = result_cache.get(name, kwargs)
            if cached is not None:
                if use_circuit_breaker:
                    circuit_breakers.record_success(name)
                return cached

        # Execute tool
        try:
            result = await tool.execute(**kwargs)
            # Record success
            if use_circuit_breaker:
                circuit_breakers.record_success(name)
            # Cache the result
            if use_cache:
                result_cache.set(name, kwargs, result)
            return result
        except Exception as e:
            # Record failure
            if use_circuit_breaker:
                circuit_breakers.record_failure(name)
            raise

    async def safe_execute(self, name: str, **kwargs) -> Any:
        """
        Safely execute a tool with full validation and error handling.

        Args:
            name: Name of the tool to execute
            **kwargs: Parameters for the tool

        Returns:
            Result of tool execution

        Raises:
            ValueError: If tool not found or parameters invalid
        """
        return await self.execute_tool(name, **kwargs)
    
    def has_tool(self, name: str) -> bool:
        """
        Check if a tool is registered.
        
        Args:
            name: Name of the tool
            
        Returns:
            True if tool exists, False otherwise
        """
        return name in self._tools


# Global tool registry instance
TOOL_REGISTRY = ToolRegistry()