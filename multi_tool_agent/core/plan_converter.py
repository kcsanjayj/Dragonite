from .graph import TaskGraph
from .node import TaskNode
from .plan_schema import ExecutionPlan


def plan_to_graph(plan: ExecutionPlan) -> TaskGraph:
    """
    Convert a validated LLM plan into our executable DAG.
    """

    graph = TaskGraph()

    for task in plan.tasks:

        graph.add_node(
            TaskNode(
                id=task.id,
                task=task.description,
                dependencies=task.dependencies,
                metadata={
                    "expected_output": task.expected_output,
                    "priority": task.priority,
                },
            )
        )

    graph.validate()

    if plan.final_task_id not in graph.nodes:
        raise ValueError(
            f"Final task '{plan.final_task_id}' "
            f"does not exist in the plan."
        )

    return graph