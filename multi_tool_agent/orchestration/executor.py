from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from multi_tool_agent.core.node import TaskNode, TaskType
from multi_tool_agent.tools import ToolManager


class Executor:
    """
    Robust DAG executor.

    Contract with AutonomousEngine:

        executor.execute_ready(graph)
            -> progress dict

        executor.get_progress(graph)
            -> progress dict

        executor.summary(graph)
            -> summary dict

    The Executor always uses the shared LLM client injected by
    AutonomousEngine.
    """

    def __init__(
        self,
        llm_client=None,
        tool_manager: ToolManager | None = None,
        max_workers: int = 4,
        retry_delay: float = 0.5,
        max_retry_delay: float = 4.0,
    ) -> None:

        self.llm_client = llm_client

        self.tool_manager = (
            tool_manager
            if tool_manager is not None
            else ToolManager()
        )

        self.max_workers = max(
            1,
            int(max_workers),
        )

        self.retry_delay = max(
            0.0,
            float(retry_delay),
        )

        self.max_retry_delay = max(
            self.retry_delay,
            float(max_retry_delay),
        )

        self.last_results: dict[str, Any] = {}

    # =========================================================
    # LLM CLIENT
    # =========================================================

    def set_llm_client(self, llm_client) -> None:
        """
        Inject the application's shared LLM client.
        """
        if llm_client is not None:
            self.llm_client = llm_client

    def _resolve_llm_client(self, graph=None):
        """
        Resolve shared LLM client.

        Priority:
            1. Executor client
            2. graph.llm_client
            3. graph.engine.llm_client
            4. graph.state.llm_client
        """

        if self.llm_client is not None:
            return self.llm_client

        if graph is not None:

            client = getattr(
                graph,
                "llm_client",
                None,
            )

            if client is not None:
                self.llm_client = client
                return client

            engine = getattr(
                graph,
                "engine",
                None,
            )

            if engine is not None:

                client = getattr(
                    engine,
                    "llm_client",
                    None,
                )

                if client is not None:
                    self.llm_client = client
                    return client

            state = getattr(
                graph,
                "state",
                None,
            )

            if state is not None:

                client = getattr(
                    state,
                    "llm_client",
                    None,
                )

                if client is not None:
                    self.llm_client = client
                    return client

        return None

    # =========================================================
    # PUBLIC API
    # =========================================================

    def execute_ready(
        self,
        graph=None,
    ) -> dict[str, Any]:
        """
        Execute all currently-ready nodes.

        IMPORTANT:
        Returns the progress dictionary directly because
        AutonomousEngine expects:

            progress = executor.execute_ready(graph)
            progress["percentage"]
        """

        if graph is None:
            raise ValueError(
                "Executor.execute_ready(graph) requires a graph."
            )

        # Resolve the shared client before workers start.
        self._resolve_llm_client(graph)

        ready_nodes = self._get_ready_nodes(graph)

        if not ready_nodes:

            progress = self.get_progress(graph)

            self._print_progress(progress)

            return progress

        print(
            f"[Executor] {len(ready_nodes)} task(s) ready."
        )

        self.last_results = {}

        worker_count = min(
            self.max_workers,
            len(ready_nodes),
        )

        with ThreadPoolExecutor(
            max_workers=worker_count
        ) as pool:

            futures = {
                pool.submit(
                    self._execute_with_retry,
                    node,
                ): node
                for node in ready_nodes
            }

            for future in as_completed(futures):

                node = futures[future]

                try:

                    result = future.result()

                    self._mark_completed(
                        node,
                        result,
                    )

                    self.last_results[
                        str(node.id)
                    ] = result

                    print(
                        f"[Executor] Completed: "
                        f"{node.id}"
                    )

                except Exception as exc:

                    self._mark_failed(
                        node,
                        exc,
                    )

                    print(
                        f"[Executor] Failed: "
                        f"{node.id}"
                    )

                    print(
                        f"[Executor] Error: "
                        f"{exc}"
                    )

        progress = self.get_progress(graph)

        self._print_progress(progress)

        return progress

    # =========================================================
    # NODE STATUS HELPERS
    # =========================================================

    @staticmethod
    def _mark_completed(
        node,
        result,
    ) -> None:

        method = getattr(
            node,
            "mark_completed",
            None,
        )

        if callable(method):
            method(result)
            return

        node.output_data = result
        node.status = "completed"

    @staticmethod
    def _mark_failed(
        node,
        exc,
    ) -> None:

        error = str(exc)

        method = getattr(
            node,
            "mark_failed",
            None,
        )

        if callable(method):

            try:
                method(error)
                return
            except Exception:
                pass

        try:
            node.error = error
        except Exception:
            pass

        try:
            node.status = "failed"
        except Exception:
            pass

    # =========================================================
    # READY NODE DISCOVERY
    # =========================================================

    @staticmethod
    def _get_ready_nodes(
        graph,
    ) -> list[Any]:

        method = getattr(
            graph,
            "get_ready_nodes",
            None,
        )

        if callable(method):

            result = method()

            if result is None:
                return []

            if isinstance(result, dict):
                return list(result.values())

            return list(result)

        nodes = getattr(
            graph,
            "nodes",
            {},
        )

        if isinstance(nodes, dict):
            nodes = nodes.values()

        ready = []

        for node in nodes:

            if Executor._status_name(node) != "pending":
                continue

            dependencies = getattr(
                node,
                "dependencies",
                None,
            )

            if dependencies is None:

                dependencies = getattr(
                    node,
                    "depends_on",
                    [],
                )

            dependencies = dependencies or []

            all_complete = True

            for dependency in dependencies:

                dependency_node = Executor._find_node(
                    graph,
                    dependency,
                )

                if dependency_node is None:
                    all_complete = False
                    break

                if (
                    Executor._status_name(
                        dependency_node
                    )
                    != "completed"
                ):
                    all_complete = False
                    break

            if all_complete:
                ready.append(node)

        return ready

    # =========================================================
    # RETRY
    # =========================================================

    def _execute_with_retry(
        self,
        node: TaskNode,
    ):

        max_retries = getattr(
            node,
            "max_retries",
            2,
        )

        try:
            max_retries = int(max_retries)
        except (
            TypeError,
            ValueError,
        ):
            max_retries = 2

        max_attempts = max(
            1,
            max_retries + 1,
        )

        for attempt in range(
            1,
            max_attempts + 1,
        ):

            try:

                print(
                    f"[Executor] Starting: "
                    f"{node.id} "
                    f"(attempt "
                    f"{attempt}/{max_attempts})"
                )

                return self._execute_node(node)

            except Exception as exc:

                try:
                    node.error = str(exc)
                except Exception:
                    pass

                print(
                    f"[Executor] "
                    f"{node.id} attempt "
                    f"{attempt} failed: "
                    f"{exc}"
                )

                if attempt >= max_attempts:
                    raise

                try:
                    node.retry_count = attempt
                except Exception:
                    pass

                delay = min(
                    self.retry_delay
                    * (2 ** (attempt - 1)),
                    self.max_retry_delay,
                )

                if delay > 0:
                    time.sleep(delay)

        raise RuntimeError(
            f"Task '{node.id}' failed."
        )

    # =========================================================
    # NODE EXECUTION
    # =========================================================

    def _execute_node(
        self,
        node: TaskNode,
    ):

        mark_running = getattr(
            node,
            "mark_running",
            None,
        )

        if callable(mark_running):
            mark_running()

        task_type = getattr(
            node,
            "task_type",
            None,
        )

        if task_type == TaskType.TOOL:
            return self._execute_tool(node)

        return self._execute_llm(node)

    # =========================================================
    # TOOL EXECUTION
    # =========================================================

    def _execute_tool(
        self,
        node: TaskNode,
    ):

        tool_name = getattr(
            node,
            "tool_name",
            None,
        )

        if not tool_name:
            raise ValueError(
                f"Tool task '{node.id}' has no tool_name."
            )

        print(
            f"[Executor] Tool task: "
            f"{node.id} -> {tool_name}"
        )

        arguments = getattr(
            node,
            "tool_arguments",
            {},
        )

        if arguments is None:
            arguments = {}

        result = self.tool_manager.execute(
            tool_name,
            arguments,
        )

        if not isinstance(result, dict):
            return result

        success = result.get(
            "success",
            True,
        )

        if not success:

            raise RuntimeError(
                result.get("error")
                or "Tool execution failed."
            )

        return result.get("result")

    # =========================================================
    # LLM EXECUTION
    # =========================================================

    def _execute_llm(
        self,
        node: TaskNode,
    ):

        client = self.llm_client

        if client is None:

            raise RuntimeError(
                "No LLM client is available "
                f"for task '{node.id}'. "
                "The shared LLM client must be "
                "passed to Executor."
            )

        prompt = self._build_llm_prompt(node)

        result = client.generate(
            system_prompt=(
                "You are an autonomous task executor.\n\n"
                "Complete the ORIGINAL TASK.\n"
                "Do not answer the task ID.\n"
                "Use INPUT DATA when provided.\n"
                "Use quality-control instructions only "
                "to improve the original task.\n\n"
                "Be accurate and concise.\n"
                "Return ONLY the result of the original task."
            ),
            user_prompt=prompt,
        )

        if result is None:
            raise RuntimeError(
                f"LLM returned no result "
                f"for task '{node.id}'."
            )

        text = str(result).strip()

        if not text:
            raise RuntimeError(
                f"LLM returned an empty result "
                f"for task '{node.id}'."
            )

        return text

    # =========================================================
    # LLM PROMPT
    # =========================================================

    @staticmethod
    def _build_llm_prompt(
        node: TaskNode,
    ) -> str:

        task = getattr(
            node,
            "task",
            "",
        )

        prompt = (
            "ORIGINAL TASK:\n"
            f"{task}\n"
        )

        input_data = getattr(
            node,
            "input_data",
            None,
        )

        if input_data is not None:

            prompt += (
                "\nINPUT DATA:\n"
                f"{input_data}\n"
            )

        metadata = getattr(
            node,
            "metadata",
            {},
        )

        if not isinstance(metadata, dict):
            metadata = {}

        repair_instructions = metadata.get(
            "repair_instructions",
            [],
        )

        if repair_instructions:

            prompt += (
                "\nQUALITY-CONTROL "
                "INSTRUCTIONS:\n"
            )

            if isinstance(
                repair_instructions,
                (list, tuple),
            ):

                for instruction in repair_instructions:

                    if isinstance(
                        instruction,
                        dict,
                    ):

                        description = instruction.get(
                            "description",
                            "",
                        )

                        if description:
                            prompt += (
                                f"- {description}\n"
                            )

                    elif instruction:

                        prompt += (
                            f"- {instruction}\n"
                        )

            else:

                prompt += (
                    f"- {repair_instructions}\n"
                )

            prompt += (
                "\nIMPORTANT:\n"
                "These instructions are quality-control "
                "instructions.\n"
                "Do NOT answer them directly.\n"
                "Use them to improve the ORIGINAL TASK.\n"
            )

        prompt += (
            "\nReturn ONLY the answer to "
            "the ORIGINAL TASK."
        )

        return prompt.strip()

    # =========================================================
    # PROGRESS
    # =========================================================

    @staticmethod
    def get_progress(
        graph=None,
    ) -> dict[str, Any]:

        if graph is None:

            return {
                "total": 0,
                "completed": 0,
                "running": 0,
                "pending": 0,
                "failed": 0,
                "repairing": 0,
                "percentage": 0.0,
            }

        nodes = Executor._get_all_nodes(graph)

        total = len(nodes)

        completed = 0
        running = 0
        pending = 0
        failed = 0
        repairing = 0

        for node in nodes:

            status = Executor._status_name(node)

            if status == "completed":
                completed += 1

            elif status == "running":
                running += 1

            elif status == "pending":
                pending += 1

            elif status == "failed":
                failed += 1

            elif status == "repairing":
                repairing += 1

        percentage = (
            completed / total * 100
            if total
            else 0.0
        )

        return {
            "total": total,
            "completed": completed,
            "running": running,
            "pending": pending,
            "failed": failed,
            "repairing": repairing,
            "percentage": round(
                percentage,
                1,
            ),
        }

    # =========================================================
    # NODE COLLECTION
    # =========================================================

    @staticmethod
    def _get_all_nodes(
        graph,
    ) -> list[Any]:

        nodes = getattr(
            graph,
            "nodes",
            {},
        )

        if nodes is None:
            return []

        if isinstance(nodes, dict):
            return list(nodes.values())

        try:
            return list(nodes)
        except TypeError:
            return []

    # =========================================================
    # NODE LOOKUP
    # =========================================================

    @staticmethod
    def _find_node(
        graph,
        task_id,
    ):

        nodes = getattr(
            graph,
            "nodes",
            {},
        )

        if isinstance(nodes, dict):

            return nodes.get(
                str(task_id)
            )

        for node in Executor._get_all_nodes(graph):

            if str(
                getattr(
                    node,
                    "id",
                    "",
                )
            ) == str(task_id):

                return node

        return None

    # =========================================================
    # STATUS
    # =========================================================

    @staticmethod
    def _status_name(
        node,
    ) -> str:

        status = getattr(
            node,
            "status",
            None,
        )

        if status is None:
            return ""

        value = getattr(
            status,
            "value",
            status,
        )

        return str(value).lower()

    # =========================================================
    # PROGRESS DISPLAY
    # =========================================================

    @staticmethod
    def _print_progress(
        progress: dict[str, Any],
    ) -> None:

        print(
            "[Executor] Progress: "
            f"{progress.get('percentage', 0.0)}%"
        )

        print(
            "[Executor] "
            f"Completed="
            f"{progress.get('completed', 0)} "
            f"Pending="
            f"{progress.get('pending', 0)} "
            f"Running="
            f"{progress.get('running', 0)} "
            f"Failed="
            f"{progress.get('failed', 0)} "
            f"Repairing="
            f"{progress.get('repairing', 0)}"
        )

    # =========================================================
    # SUMMARY
    # =========================================================

    @staticmethod
    def summary(
        graph=None,
    ) -> dict[str, Any]:

        progress = Executor.get_progress(graph)

        success = (
            progress["total"] > 0
            and progress["completed"]
            == progress["total"]
        )

        return {
            **progress,
            "success": success,
        }