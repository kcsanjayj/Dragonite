from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REPAIRING = "repairing"
    SKIPPED = "skipped"


class TaskType(str, Enum):
    LLM = "llm"
    TOOL = "tool"


@dataclass
class TaskNode:
    """
    One executable task inside the autonomous DAG.

    A task can either be:
        - LLM task
        - Tool task
    """

    id: str
    task: str

    dependencies: list[str] = field(
        default_factory=list
    )

    status: NodeStatus = NodeStatus.PENDING

    # ---------------------------------------------------------
    # Execution type
    # ---------------------------------------------------------

    task_type: TaskType = TaskType.LLM

    tool_name: str | None = None

    tool_arguments: dict[str, Any] = field(
        default_factory=dict
    )

    # ---------------------------------------------------------
    # Data
    # ---------------------------------------------------------

    input_data: Any = None
    output_data: Any = None

    error: str | None = None

    # ---------------------------------------------------------
    # Retry
    # ---------------------------------------------------------

    retry_count: int = 0
    max_retries: int = 2

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ---------------------------------------------------------
    # DAG readiness
    # ---------------------------------------------------------

    def is_ready(
        self,
        completed_nodes: set[str],
    ) -> bool:

        if self.status != NodeStatus.PENDING:
            return False

        return all(
            dependency in completed_nodes
            for dependency in self.dependencies
        )

    # ---------------------------------------------------------
    # State transitions
    # ---------------------------------------------------------

    def mark_running(self) -> None:

        self.status = NodeStatus.RUNNING

    def mark_completed(
        self,
        output: Any = None,
    ) -> None:

        self.status = NodeStatus.COMPLETED

        self.output_data = output

        self.error = None

    def mark_failed(
        self,
        error: str,
    ) -> None:

        self.status = NodeStatus.FAILED

        self.error = error

    # ---------------------------------------------------------
    # Retry
    # ---------------------------------------------------------

    def can_retry(self) -> bool:

        return self.retry_count < self.max_retries

    def prepare_retry(self) -> None:

        self.retry_count += 1

        self.status = NodeStatus.PENDING

        self.error = None

        self.output_data = None

    # ---------------------------------------------------------
    # Tool helpers
    # ---------------------------------------------------------

    def is_tool_task(self) -> bool:

        return (
            self.task_type
            == TaskType.TOOL
        )

    def is_llm_task(self) -> bool:

        return (
            self.task_type
            == TaskType.LLM
        )

    # ---------------------------------------------------------
    # Representation
    # ---------------------------------------------------------

    def __repr__(self) -> str:

        return (
            "TaskNode("
            f"id={self.id!r}, "
            f"type={self.task_type.value!r}, "
            f"status={self.status.value!r}, "
            f"dependencies="
            f"{self.dependencies!r}"
            ")"
        )