"""
Global runtime state for the autonomous agent system.
Manages the system state, execution context, and shared data.
"""

import threading
from typing import Any, Dict, List, Optional
from datetime import datetime
from .types import Plan, SystemState, NodeStatus, ExecutionResult, UserIntent


class RuntimeState:
    """
    Thread-safe global runtime state manager.
    Maintains the system state and execution context throughout the agent lifecycle.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure single state instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the runtime state."""
        if self._initialized:
            return
            
        self._state_lock = threading.RLock()
        self.system_state: SystemState = SystemState.IDLE
        self.current_plan: Optional[Plan] = None
        self.user_input: Optional[str] = None
        self.user_intent: Optional[UserIntent] = None
        self.execution_results: List[ExecutionResult] = []
        self.execution_context: Dict[str, Any] = {}
        self.metrics: Dict[str, Any] = {
            "total_nodes": 0,
            "completed_nodes": 0,
            "failed_nodes": 0,
            "total_duration_ms": 0.0,
            "replan_attempts": 0,
            "start_time": None,
            "end_time": None,
            "failure_patterns": {
                "tool_failures": 0,
                "validation_failures": 0,
                "exception_failures": 0,
                "timeout_failures": 0
            }
        }
        self.errors: List[Dict[str, Any]] = []
        self.tool_failure_counts: Dict[str, int] = {}  # Track failures per tool
        self._initialized = True
    
    def set_system_state(self, state: SystemState) -> None:
        """Set the system state."""
        with self._state_lock:
            self.system_state = state
    
    def get_system_state(self) -> SystemState:
        """Get the current system state."""
        with self._state_lock:
            return self.system_state
    
    def set_plan(self, plan: Plan) -> None:
        """Set the current execution plan."""
        with self._state_lock:
            self.current_plan = plan
            self.metrics["total_nodes"] = len(plan.nodes)
    
    def get_plan(self) -> Optional[Plan]:
        """Get the current execution plan."""
        with self._state_lock:
            return self.current_plan
    
    def set_user_input(self, user_input: str) -> None:
        """Set the user input."""
        with self._state_lock:
            self.user_input = user_input
    
    def get_user_input(self) -> Optional[str]:
        """Get the user input."""
        with self._state_lock:
            return self.user_input
    
    def set_user_intent(self, intent: UserIntent) -> None:
        """Set the detected user intent."""
        with self._state_lock:
            self.user_intent = intent
    
    def get_user_intent(self) -> Optional[UserIntent]:
        """Get the detected user intent."""
        with self._state_lock:
            return self.user_intent
    
    def add_execution_result(self, result: ExecutionResult) -> None:
        """Add an execution result."""
        with self._state_lock:
            self.execution_results.append(result)
            if result.success:
                self.metrics["completed_nodes"] += 1
            else:
                self.metrics["failed_nodes"] += 1
            if result.duration_ms:
                self.metrics["total_duration_ms"] += result.duration_ms
    
    def get_execution_results(self) -> List[ExecutionResult]:
        """Get all execution results."""
        with self._state_lock:
            return self.execution_results.copy()
    
    def update_execution_context(self, key: str, value: Any) -> None:
        """Update a value in the execution context."""
        with self._state_lock:
            self.execution_context[key] = value
    
    def get_execution_context(self) -> Dict[str, Any]:
        """Get the execution context."""
        with self._state_lock:
            return self.execution_context.copy()
    
    def get_context_value(self, key: str, default: Any = None) -> Any:
        """Get a specific value from the execution context."""
        with self._state_lock:
            return self.execution_context.get(key, default)
    
    def increment_replan_attempts(self) -> None:
        """Increment the replan attempt counter."""
        with self._state_lock:
            self.metrics["replan_attempts"] += 1
    
    def get_replan_attempts(self) -> int:
        """Get the number of replan attempts."""
        with self._state_lock:
            return self.metrics["replan_attempts"]
    
    def add_error(self, error: Dict[str, Any]) -> None:
        """Add an error to the error log."""
        with self._state_lock:
            error["timestamp"] = datetime.utcnow().isoformat()
            self.errors.append(error)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get all errors."""
        with self._state_lock:
            return self.errors.copy()
    
    def start_execution(self) -> None:
        """Mark execution start time."""
        with self._state_lock:
            self.metrics["start_time"] = datetime.utcnow().isoformat()
    
    def end_execution(self) -> None:
        """Mark execution end time."""
        with self._state_lock:
            self.metrics["end_time"] = datetime.utcnow().isoformat()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics."""
        with self._state_lock:
            return self.metrics.copy()
    
    def reset(self) -> None:
        """Reset the runtime state to initial values."""
        with self._state_lock:
            self.system_state = SystemState.IDLE
            self.current_plan = None
            self.user_input = None
            self.user_intent = None
            self.execution_results = []
            self.execution_context = {}
            self.metrics = {
                "total_nodes": 0,
                "completed_nodes": 0,
                "failed_nodes": 0,
                "total_duration_ms": 0.0,
                "replan_attempts": 0,
                "start_time": None,
                "end_time": None,
                "failure_patterns": {
                    "tool_failures": 0,
                    "validation_failures": 0,
                    "exception_failures": 0,
                    "timeout_failures": 0
                }
            }
            self.errors = []
    
    def get_node_status(self, node_id: str) -> Optional[NodeStatus]:
        """Get the status of a specific node."""
        with self._state_lock:
            if self.current_plan:
                node = self.current_plan.get_node(node_id)
                return node.status if node else None
            return None
    
    def update_node_status(self, node_id: str, status: NodeStatus, result: Any = None, error: str = None) -> None:
        """Update the status of a specific node."""
        with self._state_lock:
            if self.current_plan:
                node = self.current_plan.get_node(node_id)
                if node:
                    node.status = status
                    if result is not None:
                        node.result = result
                    if error is not None:
                        node.error = error
                    if status == NodeStatus.RUNNING:
                        node.started_at = datetime.utcnow()
                    elif status in (NodeStatus.COMPLETED, NodeStatus.FAILED):
                        node.completed_at = datetime.utcnow()
    
    def get_completed_node_ids(self) -> List[str]:
        """Get IDs of all completed nodes."""
        with self._state_lock:
            if self.current_plan:
                return [
                    node_id for node_id, node in self.current_plan.nodes.items()
                    if node.status == NodeStatus.COMPLETED
                ]
            return []
    
    def get_failed_node_ids(self) -> List[str]:
        """Get IDs of all failed nodes."""
        with self._state_lock:
            if self.current_plan:
                return [
                    node_id for node_id, node in self.current_plan.nodes.items()
                    if node.status == NodeStatus.FAILED
                ]
            return []
    
    def record_tool_failure(self, tool_name: str) -> None:
        """Record a tool failure for tracking."""
        with self._state_lock:
            self.tool_failure_counts[tool_name] = self.tool_failure_counts.get(tool_name, 0) + 1
    
    def get_tool_failure_count(self, tool_name: str) -> int:
        """Get failure count for a specific tool."""
        with self._state_lock:
            return self.tool_failure_counts.get(tool_name, 0)
    
    def should_avoid_tool(self, tool_name: str, threshold: int = 2) -> bool:
        """Check if a tool should be avoided due to repeated failures."""
        return self.get_tool_failure_count(tool_name) >= threshold
    
    def get_problematic_tools(self, threshold: int = 2) -> Dict[str, int]:
        """Get dictionary of tools that have failed multiple times."""
        with self._state_lock:
            return {
                tool: count for tool, count in self.tool_failure_counts.items()
                if count >= threshold
            }


# Global state instance
state = RuntimeState()