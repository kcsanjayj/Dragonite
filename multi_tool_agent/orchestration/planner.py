from __future__ import annotations

import json
import re
from typing import Any

from multi_tool_agent.llm_client import LLMClient
from multi_tool_agent.core.node import (
    TaskNode,
    TaskType,
)


class Planner:
    """
    Autonomous DAG planner.

    Important rules:

    - LLM tasks are used for research/reasoning.
    - Tools are used only for genuine deterministic operations.
    - Qualitative comparisons must not create fake calculator tasks.
    - Duplicate tasks are removed.
    - Invalid dependencies are removed.
    - The planner works with the project's existing graph implementation.
    """

    def __init__(
        self,
        model_client: LLMClient | None = None,
    ) -> None:

        self.model_client = (
            model_client
            or LLMClient()
        )

    # =========================================================
    # PUBLIC
    # =========================================================

    def create_plan(
        self,
        user_request: str,
    ):

        print("\n[Planner] Creating plan...")

        prompt = self._build_planning_prompt(
            user_request
        )

        raw = self.model_client.generate(
            system_prompt=(
                "You are an expert autonomous "
                "agent planner. Create a small "
                "executable DAG. Never invent "
                "tool calls for qualitative "
                "research or comparisons."
            ),
            user_prompt=prompt,
        )

        print(
            "[Planner] LLM plan received."
        )

        tasks = self._parse_plan(raw)

        tasks = self._sanitize_tasks(
            tasks,
            user_request,
        )

        graph = self._create_graph()

        for task in tasks:

            node = TaskNode(
                id=task["id"],
                task=task["task"],
                dependencies=task["dependencies"],
                task_type=(
                    TaskType.TOOL
                    if task["task_type"] == "tool"
                    else TaskType.LLM
                ),
                tool_name=task.get(
                    "tool_name"
                ),
                tool_arguments=task.get(
                    "tool_arguments",
                    {},
                ),
            )

            self._add_node(
                graph,
                node,
            )

        print(
            f"[Planner] Created DAG with "
            f"{len(graph.nodes)} tasks."
        )

        self._print_graph(graph)

        return graph

    # =========================================================
    # GRAPH CREATION
    # =========================================================

    @staticmethod
    def _create_graph():

        """
        Locate the existing TaskGraph class
        used by the project.

        This avoids assuming that TaskGraph
        lives inside core.node.
        """

        possible_modules = (
            "multi_tool_agent.core.graph",
            "multi_tool_agent.core.task_graph",
            "multi_tool_agent.core.dag",
            "multi_tool_agent.orchestration.graph",
            "multi_tool_agent.orchestration.task_graph",
        )

        for module_name in possible_modules:

            try:

                module = __import__(
                    module_name,
                    fromlist=["TaskGraph"],
                )

                graph_class = getattr(
                    module,
                    "TaskGraph",
                    None,
                )

                if graph_class is not None:
                    return graph_class()

            except (
                ImportError,
                ModuleNotFoundError,
            ):
                continue

        raise ImportError(
            "TaskGraph could not be located. "
            "Expected it in one of: "
            + ", ".join(
                possible_modules
            )
        )

    # =========================================================
    # GRAPH ADD
    # =========================================================

    @staticmethod
    def _add_node(
        graph,
        node: TaskNode,
    ) -> None:

        if hasattr(
            graph,
            "add_node",
        ):

            graph.add_node(node)
            return

        if hasattr(
            graph,
            "add",
        ):

            graph.add(node)
            return

        if hasattr(
            graph,
            "nodes",
        ) and isinstance(
            graph.nodes,
            dict,
        ):

            graph.nodes[node.id] = node
            return

        raise AttributeError(
            "TaskGraph does not provide "
            "add_node(), add(), or a "
            "mutable nodes dictionary."
        )

    # =========================================================
    # PLANNING PROMPT
    # =========================================================

    @staticmethod
    def _build_planning_prompt(
        user_request: str,
    ) -> str:

        return f"""
Create a minimal executable DAG for:

{user_request}

STRICT RULES:

1. Research, comparison, reasoning,
   evaluation and recommendation are
   LLM tasks.

2. A calculator TOOL may ONLY be used
   when the user explicitly asks for
   arithmetic or deterministic calculation.

3. NEVER create calculator tasks merely
   because the request mentions:

   - performance
   - speed
   - API
   - benchmark
   - scalability
   - comparison
   - reliability

4. NEVER invent benchmark numbers.

5. For comparing Python and Rust,
   use research and reasoning tasks.

6. Avoid duplicate tasks.

7. Every dependency must refer to
   another task ID.

8. Keep the DAG small.

9. The final recommendation must depend
   on the comparison/evaluation tasks.

Return ONLY JSON.

Example:

{{
  "tasks": [
    {{
      "id": "research_python",
      "task": "Research Python for the request",
      "dependencies": [],
      "task_type": "llm"
    }},
    {{
      "id": "research_rust",
      "task": "Research Rust for the request",
      "dependencies": [],
      "task_type": "llm"
    }},
    {{
      "id": "compare",
      "task": "Compare Python and Rust",
      "dependencies": [
        "research_python",
        "research_rust"
      ],
      "task_type": "llm"
    }},
    {{
      "id": "recommend",
      "task": "Recommend the better option",
      "dependencies": [
        "compare"
      ],
      "task_type": "llm"
    }}
  ]
}}

User request:

{user_request}
""".strip()

    # =========================================================
    # JSON PARSER
    # =========================================================

    @staticmethod
    def _parse_plan(
        raw: str,
    ) -> list[dict[str, Any]]:

        text = raw.strip()

        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

        try:

            data = json.loads(text)

        except json.JSONDecodeError:

            match = re.search(
                r"\{.*\}",
                text,
                flags=re.DOTALL,
            )

            if not match:

                raise ValueError(
                    "Planner returned invalid JSON."
                )

            data = json.loads(
                match.group(0)
            )

        tasks = data.get(
            "tasks",
            [],
        )

        if not isinstance(
            tasks,
            list,
        ):

            raise ValueError(
                "Planner 'tasks' must be a list."
            )

        return tasks

    # =========================================================
    # SANITIZATION
    # =========================================================

    def _sanitize_tasks(
        self,
        tasks: list[dict[str, Any]],
        user_request: str,
    ) -> list[dict[str, Any]]:

        cleaned = []

        existing_ids = set()

        for task in tasks:

            if not isinstance(
                task,
                dict,
            ):
                continue

            task_id = str(
                task.get(
                    "id",
                    "",
                )
            ).strip()

            description = str(
                task.get(
                    "task",
                    "",
                )
            ).strip()

            if not task_id or not description:
                continue

            task_id = re.sub(
                r"[^a-zA-Z0-9_]+",
                "_",
                task_id,
            ).strip("_").lower()

            if task_id in existing_ids:
                continue

            existing_ids.add(
                task_id
            )

            dependencies = task.get(
                "dependencies",
                [],
            )

            if not isinstance(
                dependencies,
                list,
            ):
                dependencies = []

            dependencies = [
                str(dep).strip()
                for dep in dependencies
                if str(dep).strip()
            ]

            task_type = str(
                task.get(
                    "task_type",
                    "llm",
                )
            ).lower().strip()

            if task_type not in {
                "llm",
                "tool",
            }:

                task_type = "llm"

            tool_name = task.get(
                "tool_name"
            )

            tool_arguments = task.get(
                "tool_arguments",
                {},
            )

            # -------------------------------------------------
            # Prevent fake calculator tasks.
            # -------------------------------------------------

            if self._is_fake_calculation(
                task_id=task_id,
                description=description,
                user_request=user_request,
                task_type=task_type,
                tool_name=tool_name,
            ):

                print(
                    "[Planner] Removed invalid "
                    f"calculator task: {task_id}"
                )

                task_type = "llm"
                tool_name = None
                tool_arguments = {}

                description = (
                    "Analyze the relevant "
                    "information without "
                    "inventing unsupported "
                    "benchmark numbers."
                )

            cleaned.append(
                {
                    "id": task_id,
                    "task": description,
                    "dependencies": dependencies,
                    "task_type": task_type,
                    "tool_name": tool_name,
                    "tool_arguments": (
                        tool_arguments
                        if isinstance(
                            tool_arguments,
                            dict,
                        )
                        else {}
                    ),
                }
            )

        valid_ids = {
            task["id"]
            for task in cleaned
        }

        for task in cleaned:

            task["dependencies"] = [
                dependency
                for dependency in task[
                    "dependencies"
                ]
                if (
                    dependency in valid_ids
                    and dependency != task["id"]
                )
            ]

        if not cleaned:

            cleaned = self._fallback_plan(
                user_request
            )

        return cleaned

    # =========================================================
    # FAKE CALCULATOR DETECTION
    # =========================================================

    @staticmethod
    def _is_fake_calculation(
        task_id: str,
        description: str,
        user_request: str,
        task_type: str,
        tool_name: str | None,
    ) -> bool:

        if task_type != "tool":
            return False

        if tool_name != "calculator":
            return False

        request = user_request.lower()

        task_text = (
            f"{task_id} "
            f"{description}"
        ).lower()

        explicit_math = any(
            word in request
            for word in (
                "calculate",
                "compute",
                "arithmetic",
                "equation",
                "percentage",
                "average",
            )
        )

        comparison = any(
            word in request
            for word in (
                "compare",
                "comparison",
                "recommend",
                "performance",
                "scalability",
                "reliability",
                "api",
                "python",
                "rust",
            )
        )

        fake_benchmark = any(
            word in task_text
            for word in (
                "benchmark",
                "performance",
                "api",
                "python",
                "rust",
            )
        )

        return (
            comparison
            and fake_benchmark
            and not explicit_math
        )

    # =========================================================
    # FALLBACK
    # =========================================================

    @staticmethod
    def _fallback_plan(
        user_request: str,
    ) -> list[dict[str, Any]]:

        return [
            {
                "id": "research_python",
                "task": (
                    "Research Python's strengths, "
                    "weaknesses, performance, "
                    "ecosystem and suitability."
                ),
                "dependencies": [],
                "task_type": "llm",
                "tool_name": None,
                "tool_arguments": {},
            },
            {
                "id": "research_rust",
                "task": (
                    "Research Rust's strengths, "
                    "weaknesses, performance, "
                    "ecosystem and suitability."
                ),
                "dependencies": [],
                "task_type": "llm",
                "tool_name": None,
                "tool_arguments": {},
            },
            {
                "id": "compare_python_and_rust",
                "task": (
                    "Compare Python and Rust "
                    "using the research results."
                ),
                "dependencies": [
                    "research_python",
                    "research_rust",
                ],
                "task_type": "llm",
                "tool_name": None,
                "tool_arguments": {},
            },
            {
                "id": "evaluate_tradeoffs",
                "task": (
                    "Evaluate the practical "
                    "trade-offs between Python "
                    "and Rust."
                ),
                "dependencies": [
                    "research_python",
                    "research_rust",
                ],
                "task_type": "llm",
                "tool_name": None,
                "tool_arguments": {},
            },
            {
                "id": "recommend",
                "task": (
                    "Recommend Python or Rust "
                    "based on the comparison "
                    "and trade-offs."
                ),
                "dependencies": [
                    "compare_python_and_rust",
                    "evaluate_tradeoffs",
                ],
                "task_type": "llm",
                "tool_name": None,
                "tool_arguments": {},
            },
        ]

    # =========================================================
    # GRAPH DISPLAY
    # =========================================================

    @staticmethod
    def _print_graph(
        graph,
    ) -> None:

        print("\n[Planner] DAG:")

        for node in graph.nodes.values():

            if node.task_type == TaskType.TOOL:

                label = (
                    f"{node.id} "
                    f"[TOOL → "
                    f"{node.tool_name}]"
                )

            else:

                label = (
                    f"{node.id} [LLM]"
                )

            dependencies = (
                ", ".join(
                    node.dependencies
                )
                if node.dependencies
                else "none"
            )

            print(
                f"  {label} "
                f"<- [{dependencies}]"
            )