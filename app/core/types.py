"""
Core type schemas for the autonomous agent system.
Defines Plan, Node, Edge, Result, and other fundamental data structures.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class NodeStatus(str, Enum):
    """Status of a node in the execution graph."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ToolCall(BaseModel):
    """Represents a tool invocation."""
    tool_name: str = Field(..., description="Name of the tool to call")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the tool")
    timeout: Optional[int] = Field(default=30, description="Timeout in seconds")


class Node(BaseModel):
    """Represents a single node in the execution DAG."""
    id: str = Field(..., description="Unique identifier for the node")
    type: str = Field(..., description="Type of node (tool_call, decision, etc.)")
    description: str = Field(..., description="Human-readable description")
    tool_call: Optional[ToolCall] = Field(default=None, description="Tool invocation if applicable")
    dependencies: Set[str] = Field(default_factory=set, description="IDs of nodes this node depends on")
    status: NodeStatus = Field(default=NodeStatus.PENDING, description="Current status")
    result: Optional[Any] = Field(default=None, description="Result of execution")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None, description="When execution started")
    completed_at: Optional[datetime] = Field(default=None, description="When execution completed")

    @field_validator('dependencies')
    @classmethod
    def validate_dependencies(cls, v):
        """Ensure dependencies are valid."""
        if not isinstance(v, set):
            v = set(v)
        return v

    def is_ready(self, completed_nodes: Set[str]) -> bool:
        """Check if node is ready to execute based on dependencies."""
        return self.status == NodeStatus.PENDING and self.dependencies.issubset(completed_nodes)


class Edge(BaseModel):
    """Represents a directed edge in the execution DAG."""
    from_node: str = Field(..., description="Source node ID")
    to_node: str = Field(..., description="Target node ID")
    condition: Optional[str] = Field(default=None, description="Optional condition for traversal")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Plan(BaseModel):
    """Represents the complete execution plan as a DAG."""
    id: str = Field(..., description="Unique plan identifier")
    nodes: Dict[str, Node] = Field(default_factory=dict, description="All nodes in the plan")
    edges: List[Edge] = Field(default_factory=list, description="All edges in the plan")
    goal: str = Field(..., description="The overall goal of the plan")
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution context")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Plan metadata")

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def add_node(self, node: Node) -> None:
        """Add a node to the plan."""
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the plan."""
        self.edges.append(edge)

    def get_ready_nodes(self) -> List[Node]:
        """Get all nodes that are ready to execute, sorted by priority."""
        completed = {nid for nid, node in self.nodes.items() if node.status == NodeStatus.COMPLETED}
        ready = [node for node in self.nodes.values() if node.is_ready(completed)]

        # Priority scheduling: fewer dependencies = higher priority, lower estimated cost = higher priority
        def score_node(node):
            # Fewer dependencies = can run sooner = higher score
            dep_score = -len(node.dependencies)
            # Estimated cost (from metadata or default 0)
            cost = node.metadata.get("estimated_cost", 0)
            cost_score = -cost * 0.1
            return dep_score + cost_score

        return sorted(ready, key=score_node, reverse=True)

    def is_complete(self) -> bool:
        """Check if all nodes are completed or failed."""
        return all(
            node.status in (NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED)
            for node in self.nodes.values()
        )

    def get_failed_nodes(self) -> List[Node]:
        """Get all failed nodes."""
        return [node for node in self.nodes.values() if node.status == NodeStatus.FAILED]


class ExecutionResult(BaseModel):
    """Result of a single node execution."""
    node_id: str = Field(..., description="ID of the executed node")
    success: bool = Field(..., description="Whether execution succeeded")
    result: Optional[Any] = Field(default=None, description="Execution result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    duration_ms: Optional[float] = Field(default=None, description="Execution duration in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SystemState(str, Enum):
    """Overall system state."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    REPLANNING = "replanning"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    ERROR = "error"


class IntentType(str, Enum):
    """Types of user intents."""
    QUERY = "query"
    TASK = "task"
    ANALYSIS = "analysis"
    CODE = "code"
    RESEARCH = "research"
    UNKNOWN = "unknown"


class UserIntent(BaseModel):
    """Detected user intent."""
    type: IntentType = Field(..., description="Type of intent")
    confidence: float = Field(..., description="Confidence score (0-1)")
    workflow: str = Field(..., description="Suggested workflow")
    reasoning: str = Field(..., description="Reasoning for intent classification")


class ValidationRule(BaseModel):
    """A validation rule for execution results."""
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    check_fn: str = Field(..., description="Function name to perform validation")
    severity: str = Field(default="error", description="Severity: error, warning, info")


class ValidationResult(BaseModel):
    """Result of a validation check."""
    rule_name: str = Field(..., description="Name of the rule")
    passed: bool = Field(..., description="Whether validation passed")
    message: str = Field(..., description="Validation message")
    severity: str = Field(default="info", description="Severity of the result")


class ReplanRequest(BaseModel):
    """Request to replan after failure."""
    failed_node_id: str = Field(..., description="ID of the failed node")
    error_message: str = Field(..., description="Error that caused failure")
    context: Dict[str, Any] = Field(default_factory=dict, description="Current execution context")
    attempt_count: int = Field(default=1, description="Number of replan attempts")
    failure_history: List[Dict[str, Any]] = Field(default_factory=list, description="Recent failure patterns")
    failure_patterns: Dict[str, int] = Field(default_factory=dict, description="Aggregated failure pattern counts")
    completed_results: Dict[str, Any] = Field(default_factory=dict, description="Results from successfully completed nodes")