from .node import NodeStatus, TaskNode


class TaskGraph:
    """
    Directed Acyclic Graph of autonomous tasks.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, TaskNode] = {}

    def add_node(self, node: TaskNode) -> None:

        if node.id in self.nodes:
            raise ValueError(
                f"Node already exists: {node.id}"
            )

        self.nodes[node.id] = node

    def get_node(self, node_id: str) -> TaskNode:

        if node_id not in self.nodes:
            raise KeyError(
                f"Unknown node: {node_id}"
            )

        return self.nodes[node_id]

    def validate(self) -> None:
        """
        Validate dependencies and detect cycles.
        """

        # Check dependencies exist.
        for node in self.nodes.values():

            for dependency in node.dependencies:

                if dependency not in self.nodes:
                    raise ValueError(
                        f"Node '{node.id}' depends on "
                        f"unknown node '{dependency}'."
                    )

                if dependency == node.id:
                    raise ValueError(
                        f"Node '{node.id}' cannot depend on itself."
                    )

        # Cycle detection.
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:

            if node_id in visiting:
                raise ValueError(
                    f"Cycle detected involving '{node_id}'."
                )

            if node_id in visited:
                return

            visiting.add(node_id)

            node = self.nodes[node_id]

            for dependency in node.dependencies:
                visit(dependency)

            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in self.nodes:
            visit(node_id)

    def get_completed_nodes(self) -> set[str]:

        return {
            node_id
            for node_id, node in self.nodes.items()
            if node.status == NodeStatus.COMPLETED
        }

    def get_ready_nodes(self) -> list[TaskNode]:

        completed = self.get_completed_nodes()

        return [
            node
            for node in self.nodes.values()
            if node.is_ready(completed)
        ]

    def mark_running(self, node_id: str) -> None:
        self.get_node(node_id).mark_running()

    def mark_completed(
        self,
        node_id: str,
        output=None,
    ) -> None:

        self.get_node(node_id).mark_completed(output)

    def mark_failed(
        self,
        node_id: str,
        error: str,
    ) -> None:

        self.get_node(node_id).mark_failed(error)

    def get_failed_nodes(self) -> list[TaskNode]:

        return [
            node
            for node in self.nodes.values()
            if node.status == NodeStatus.FAILED
        ]

    def get_pending_nodes(self) -> list[TaskNode]:

        return [
            node
            for node in self.nodes.values()
            if node.status == NodeStatus.PENDING
        ]

    def is_complete(self) -> bool:

        return bool(self.nodes) and all(
            node.status == NodeStatus.COMPLETED
            for node in self.nodes.values()
        )

    def has_failed_nodes(self) -> bool:

        return any(
            node.status == NodeStatus.FAILED
            for node in self.nodes.values()
        )

    def summary(self) -> dict[str, int]:

        result: dict[str, int] = {}

        for node in self.nodes.values():

            status = node.status.value

            result[status] = (
                result.get(status, 0) + 1
            )

        return result

    def __repr__(self) -> str:

        return (
            f"TaskGraph("
            f"nodes={list(self.nodes.keys())!r}"
            f")"
        )