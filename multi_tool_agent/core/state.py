from dataclasses import dataclass, field
from typing import Any

from multi_tool_agent.core.graph import TaskGraph


@dataclass
class AgentState:

    user_request: str

    graph: TaskGraph | None = None

    route: dict[str, Any] = field(default_factory=dict)

    node_outputs: dict[str, Any] = field(default_factory=dict)

    critique: dict[str, Any] = field(default_factory=dict)

    repair_history: list[dict[str, Any]] = field(default_factory=list)

    iteration: int = 0
    max_iterations: int = 5

    final_response: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def can_continue(self) -> bool:
        return self.iteration < self.max_iterations

    def next_iteration(self) -> None:
        self.iteration += 1

    def record_output(
        self,
        node_id: str,
        output: Any,
    ) -> None:
        self.node_outputs[node_id] = output

    def record_repair(
        self,
        repair: dict[str, Any],
    ) -> None:
        self.repair_history.append(repair)

    def set_final_response(
        self,
        response: str,
    ) -> None:
        self.final_response = response