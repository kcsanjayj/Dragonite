from __future__ import annotations

from typing import Any

from multi_tool_agent.core.state import AgentState

from multi_tool_agent.orchestration.planner import Planner
from multi_tool_agent.orchestration.executor import Executor
from multi_tool_agent.orchestration.critic import Critic
from multi_tool_agent.orchestration.replanner import Replanner
from multi_tool_agent.orchestration.synthesizer import Synthesizer

from multi_tool_agent.memory import MemoryContext

from multi_tool_agent.observability import (
    Tracer,
    AgentLogger,
)


class AutonomousEngine:
    """
    Main autonomous execution engine.

    Pipeline:

        User Request
             ↓
        Memory
             ↓
        Planning
             ↓
        DAG Execution
             ↓
        Criticism
             ↓
        Repair / Replanning
             ↓
        Execution
             ↓
        Synthesis
             ↓
        Memory
             ↓
        Final Answer
    """

    def __init__(
        self,
        planner: Planner | None = None,
        executor: Executor | None = None,
        critic: Critic | None = None,
        replanner: Replanner | None = None,
        synthesizer: Synthesizer | None = None,
        tracer: Tracer | None = None,
        logger: AgentLogger | None = None,
        memory: MemoryContext | None = None,
        max_cycles: int = 5,
        llm_client=None,
    ) -> None:

        if max_cycles < 1:
            raise ValueError(
                "max_cycles must be at least 1."
            )

        self.max_cycles = int(max_cycles)
        self.memory = memory

        # =====================================================
        # SHARED LLM CLIENT
        # =====================================================

        self._llm_client = llm_client

        # =====================================================
        # PLANNER
        # =====================================================

        if planner is not None:
            self.planner = planner
        else:
            if llm_client is not None:
                try:
                    self.planner = Planner(
                        llm_client=llm_client
                    )
                except TypeError:
                    self.planner = Planner()
            else:
                self.planner = Planner()

        # Try to recover LLM client from planner if one was
        # created internally.
        if self._llm_client is None:
            self._llm_client = self._get_component_llm(
                self.planner
            )

        # =====================================================
        # EXECUTOR
        # =====================================================

        if executor is not None:
            self.executor = executor
        else:
            self.executor = Executor(
                llm_client=self._llm_client
            )

        # CRITICAL:
        # Always inject the shared LLM into Executor.
        self._inject_llm(
            self.executor,
            self._llm_client
        )

        # =====================================================
        # CRITIC
        # =====================================================

        self.critic = (
            critic
            if critic is not None
            else Critic()
        )

        # =====================================================
        # REPLANNER
        # =====================================================

        self.replanner = (
            replanner
            if replanner is not None
            else Replanner()
        )

        # =====================================================
        # SYNTHESIZER
        # =====================================================

        if synthesizer is not None:
            self.synthesizer = synthesizer
        else:
            try:
                self.synthesizer = Synthesizer(
                    llm_client=self._llm_client
                )
            except TypeError:
                self.synthesizer = Synthesizer()

        self._inject_llm(
            self.synthesizer,
            self._llm_client
        )

        # =====================================================
        # OBSERVABILITY
        # =====================================================

        self.tracer = (
            tracer
            if tracer is not None
            else Tracer()
        )

        self.logger = (
            logger
            if logger is not None
            else AgentLogger()
        )

        print(
            "[Engine] AutonomousEngine initialized"
        )

        print(
            "[Engine] Shared LLM client: "
            f"{self._shared_llm_enabled()}"
        )

        print(
            "[Engine] Maximum autonomous cycles: "
            f"{self.max_cycles}"
        )

    # =========================================================
    # LLM HELPERS
    # =========================================================

    @staticmethod
    def _get_component_llm(
        component,
    ):
        if component is None:
            return None

        for attribute in (
            "llm_client",
            "model_client",
        ):
            client = getattr(
                component,
                attribute,
                None,
            )

            if client is not None:
                return client

        return None

    @staticmethod
    def _inject_llm(
        component,
        llm_client,
    ) -> None:

        if component is None:
            return

        if llm_client is None:
            return

        setter = getattr(
            component,
            "set_llm_client",
            None,
        )

        if callable(setter):
            try:
                setter(llm_client)
                return
            except Exception:
                pass

        try:
            component.llm_client = llm_client
        except Exception:
            pass

    # =========================================================
    # PUBLIC API
    # =========================================================

    def run(
        self,
        user_request: str,
    ) -> dict[str, Any]:

        if not user_request or not str(
            user_request
        ).strip():

            raise ValueError(
                "user_request cannot be empty."
            )

        user_request = str(
            user_request
        ).strip()

        run_id = self.tracer.start_run(
            user_request
        )

        print()
        print("=" * 70)
        print("AUTONOMOUS AGENT STARTING")
        print("=" * 70)

        print()
        print("[Engine] Request:")
        print(user_request)

        try:

            self.tracer.record(
                "request_received",
                run_id,
                {
                    "request": user_request
                },
            )

            # =================================================
            # INITIAL STATE
            # =================================================

            state = AgentState(
                user_request=user_request
            )

            # =================================================
            # PHASE 0 — MEMORY
            # =================================================

            print()
            print(
                "[Engine] Phase 0: Memory Retrieval"
            )

            memory_context = (
                self._retrieve_memory(
                    user_request
                )
            )

            if memory_context:
                print(
                    "[Engine] Relevant memory found."
                )
            else:
                print(
                    "[Engine] No relevant memory found."
                )

            # =================================================
            # PHASE 1 — PLANNING
            # =================================================

            print()
            print(
                "[Engine] Phase 1: Planning"
            )

            graph = self.planner.create_plan(
                user_request
            )

            if graph is None:
                raise RuntimeError(
                    "Planner returned no graph."
                )

            state.graph = graph

            # Make the shared LLM available through the graph
            # when possible.
            try:
                graph.llm_client = (
                    self._llm_client
                )
            except Exception:
                pass

            self._print_graph(
                graph
            )

            # =================================================
            # AUTONOMOUS CONTROL
            # =================================================

            accepted_nodes: set[str] = set()

            cycle = 0
            completed_early = False

            while (
                cycle < self.max_cycles
            ):

                cycle += 1

                print()
                print("=" * 60)
                print(
                    "[Engine] AUTONOMOUS CYCLE "
                    f"{cycle}/{self.max_cycles}"
                )
                print("=" * 60)

                # =================================================
                # PHASE 2 — EXECUTION
                # =================================================

                print()
                print(
                    "[Engine] Phase 2: Execution"
                )

                execution_result = (
                    self.executor.execute_ready(
                        graph
                    )
                )

                progress = (
                    self._normalize_progress(
                        execution_result,
                        graph,
                    )
                )

                print(
                    "[Engine] Progress: "
                    f"{progress['percentage']}%"
                )

                # =================================================
                # FAILED TASKS
                # =================================================

                if progress["failed"] > 0:

                    print(
                        "[Engine] "
                        f"{progress['failed']} task(s) failed."
                    )

                    # Let critic/replanner decide whether
                    # repairs are possible.

                # =================================================
                # ALL TASKS COMPLETE
                # =================================================

                if self._all_tasks_completed(
                    graph
                ):

                    print()
                    print(
                        "[Engine] "
                        "ALL TASKS COMPLETED."
                    )

                    completed_early = True
                    break

                # =================================================
                # PHASE 3 — CRITICISM
                # =================================================

                print()
                print(
                    "[Engine] Phase 3: Criticism"
                )

                criticism = (
                    self._evaluate_newly_completed(
                        graph,
                        state,
                        accepted_nodes,
                    )
                )

                print(
                    "[Engine] Criticism results: "
                    f"{len(criticism)} task(s)"
                )

                repairs = (
                    self._extract_repairs(
                        criticism
                    )
                )

                print(
                    "[Engine] Repairs required: "
                    f"{len(repairs)}"
                )

                # =================================================
                # NO REPAIRS
                # =================================================

                if not repairs:

                    if self._all_tasks_completed(
                        graph
                    ):

                        completed_early = True
                        break

                    # If failed tasks exist and nothing can repair
                    # them, don't endlessly loop.
                    if (
                        progress["failed"] > 0
                        and progress["pending"] == 0
                    ):
                        print(
                            "[Engine] "
                            "No repair available for failed tasks."
                        )
                        break

                    print(
                        "[Engine] "
                        "No repairs required. "
                        "Waiting for dependency tasks."
                    )

                    continue

                # =================================================
                # PHASE 4 — REPAIR
                # =================================================

                print()
                print(
                    "[Engine] Phase 4: "
                    "Replanning / Repair"
                )

                repair_result = (
                    self.replanner.repair(
                        graph,
                        criticism,
                    )
                )

                print(
                    "[Engine] Repair result:"
                )

                print(
                    repair_result
                )

                # Remove repaired nodes from accepted set.
                for item in repairs:

                    if isinstance(
                        item,
                        tuple,
                    ):

                        task_id = item[0]

                        if task_id:
                            accepted_nodes.discard(
                                str(task_id)
                            )

                # =================================================
                # IMMEDIATE REPAIR EXECUTION
                # =================================================

                print()
                print(
                    "[Engine] "
                    "Executing repaired tasks immediately..."
                )

                repair_execution = (
                    self.executor.execute_ready(
                        graph
                    )
                )

                repair_progress = (
                    self._normalize_progress(
                        repair_execution,
                        graph,
                    )
                )

                print(
                    "[Engine] "
                    "Repair execution progress: "
                    f"{repair_progress['percentage']}%"
                )

                # =================================================
                # POST-REPAIR CRITICISM
                # =================================================

                repaired_criticism = (
                    self._evaluate_newly_completed(
                        graph,
                        state,
                        accepted_nodes,
                    )
                )

                print(
                    "[Engine] "
                    "Post-repair criticism: "
                    f"{len(repaired_criticism)} task(s)"
                )

                second_repairs = (
                    self._extract_repairs(
                        repaired_criticism
                    )
                )

                print(
                    "[Engine] "
                    "Post-repair repairs required: "
                    f"{len(second_repairs)}"
                )

                # =================================================
                # SUCCESS AFTER REPAIR
                # =================================================

                if (
                    self._all_tasks_completed(
                        graph
                    )
                    and not second_repairs
                ):

                    print()
                    print(
                        "[Engine] "
                        "ALL TASKS COMPLETED "
                        "AFTER REPAIR."
                    )

                    completed_early = True
                    break

            # =====================================================
            # MAX CYCLES
            # =====================================================

            if not completed_early:

                print()
                print(
                    "[Engine] "
                    "Maximum autonomous cycles reached."
                )

            # =====================================================
            # PHASE 5 — SYNTHESIS
            # =====================================================

            print()
            print(
                "[Engine] Phase 5: Synthesis"
            )

            answer = self._synthesize(
                user_request,
                graph,
            )

            # =====================================================
            # PHASE 6 — MEMORY
            # =====================================================

            print()
            print(
                "[Engine] Phase 6: Memory"
            )

            memory_saved = (
                self._save_memory(
                    user_request,
                    graph,
                    answer,
                )
            )

            # =====================================================
            # FINAL STATUS
            # =====================================================

            progress = (
                self._get_progress(
                    graph
                )
            )

            success = (
                progress["total"] > 0
                and progress["completed"]
                == progress["total"]
                and progress["failed"] == 0
                and progress["pending"] == 0
                and progress["repairing"] == 0
            )

            result = {
                "success": success,
                "run_id": run_id,
                "answer": answer,
                "progress": progress,
                "memory_saved": memory_saved,
                "cycles_used": cycle,
                "max_cycles": self.max_cycles,
                "trace": self.tracer.read_run(
                    run_id
                ),
            }

            print()

            if success:

                print("=" * 70)
                print(
                    "[Engine] RUN COMPLETED SUCCESSFULLY"
                )
                print("=" * 70)

            else:

                print("=" * 70)
                print(
                    "[Engine] RUN COMPLETED "
                    "WITH INCOMPLETE TASKS"
                )
                print("=" * 70)

            print(
                "[Engine] Final progress:",
                progress,
            )

            print(
                "[Engine] Cycles used:",
                cycle,
            )

            self.tracer.end_run(
                run_id,
                success,
                {
                    "progress": progress,
                    "cycles_used": cycle,
                },
            )

            return result

        except Exception as exc:

            print()
            print("=" * 70)
            print(
                "[Engine] RUN FAILED"
            )
            print(
                f"[Engine] Error: {exc}"
            )
            print("=" * 70)

            try:
                self.tracer.record(
                    "run_failed",
                    run_id,
                    {
                        "error": str(exc)
                    },
                )

                self.tracer.end_run(
                    run_id,
                    False,
                    {
                        "error": str(exc)
                    },
                )
            except Exception:
                pass

            raise

    # =========================================================
    # PROGRESS NORMALIZATION
    # =========================================================

    def _normalize_progress(
        self,
        result,
        graph,
    ) -> dict[str, Any]:

        if isinstance(
            result,
            dict,
        ):

            # Direct progress object.
            if "percentage" in result:

                return {
                    "total": int(
                        result.get(
                            "total",
                            0,
                        )
                    ),
                    "completed": int(
                        result.get(
                            "completed",
                            0,
                        )
                    ),
                    "running": int(
                        result.get(
                            "running",
                            0,
                        )
                    ),
                    "pending": int(
                        result.get(
                            "pending",
                            0,
                        )
                    ),
                    "failed": int(
                        result.get(
                            "failed",
                            0,
                        )
                    ),
                    "repairing": int(
                        result.get(
                            "repairing",
                            0,
                        )
                    ),
                    "percentage": float(
                        result.get(
                            "percentage",
                            0.0,
                        )
                    ),
                }

            # Executor result wrapper.
            progress = result.get(
                "progress"
            )

            if isinstance(
                progress,
                dict,
            ):

                return self._normalize_progress(
                    progress,
                    graph,
                )

        return self._get_progress(
            graph
        )

    # =========================================================
    # CRITIC
    # =========================================================

    def _evaluate_newly_completed(
        self,
        graph,
        state,
        accepted_nodes: set[str],
    ) -> dict:

        results = {}

        nodes = getattr(
            graph,
            "nodes",
            {},
        )

        if not isinstance(
            nodes,
            dict,
        ):
            return results

        for node in nodes.values():

            status = getattr(
                node,
                "status",
                None,
            )

            status_value = getattr(
                status,
                "value",
                status,
            )

            if str(
                status_value
            ).lower() != "completed":
                continue

            task_id = str(
                getattr(
                    node,
                    "id",
                    "",
                )
            )

            if task_id in accepted_nodes:
                continue

            try:

                result = self.critic.evaluate(
                    node
                )

            except Exception as exc:

                print(
                    "[Engine] Critic error for "
                    f"{task_id}: {exc}"
                )

                result = {
                    "status": "pass_with_warning",
                    "score": 7,
                    "issues": [
                        {
                            "type": "critic_error",
                            "description": str(
                                exc
                            ),
                        }
                    ],
                    "repair_instructions": [],
                    "reason": (
                        "Critic failed; "
                        "allowing task to continue."
                    ),
                }

            if not isinstance(
                result,
                dict,
            ):

                result = {
                    "status": "pass_with_warning",
                    "score": 7,
                    "issues": [],
                    "repair_instructions": [],
                }

            results[
                task_id
            ] = result

            status = str(
                result.get(
                    "status",
                    "",
                )
            ).lower()

            if status not in {
                "repair",
                "repair_required",
                "fail",
            }:

                accepted_nodes.add(
                    task_id
                )

                print(
                    "[Engine] Accepted: "
                    f"{task_id} "
                    f"(score="
                    f"{result.get('score')})"
                )

            else:

                print(
                    "[Engine] Repair required: "
                    f"{task_id}"
                )

        return results

    # =========================================================
    # MEMORY
    # =========================================================

    def _retrieve_memory(
        self,
        user_request: str,
    ) -> Any:

        if self.memory is None:
            return None

        for method_name in (
            "retrieve",
            "search",
            "get_relevant",
            "recall",
        ):

            method = getattr(
                self.memory,
                method_name,
                None,
            )

            if not callable(method):
                continue

            try:

                return method(
                    user_request
                )

            except TypeError:

                try:
                    return method(
                        query=user_request
                    )
                except Exception:
                    continue

            except Exception:
                continue

        return None

    def _save_memory(
        self,
        user_request: str,
        graph,
        answer: Any,
    ) -> bool:

        if self.memory is None:
            return False

        payload = {
            "user_request": user_request,
            "answer": answer,
            "outputs": self._collect_outputs(
                graph
            ),
        }

        for method_name in (
            "save",
            "store",
            "remember",
            "add",
        ):

            method = getattr(
                self.memory,
                method_name,
                None,
            )

            if not callable(method):
                continue

            try:

                method(
                    payload
                )

                return True

            except TypeError:

                try:

                    method(
                        user_request,
                        payload,
                    )

                    return True

                except Exception:
                    continue

            except Exception:
                continue

        return False

    # =========================================================
    # SYNTHESIS
    # =========================================================

    def _synthesize(
        self,
        user_request: str,
        graph,
    ) -> str:

        outputs = (
            self._collect_outputs(
                graph
            )
        )

        if not outputs:

            return (
                "No usable task results were produced."
            )

        try:

            answer = (
                self.synthesizer.synthesize(
                    user_request,
                    graph,
                )
            )

        except TypeError:

            answer = (
                self.synthesizer.synthesize(
                    user_request,
                    outputs,
                )
            )

        except Exception as exc:

            print(
                "[Engine] Synthesis failed: "
                f"{exc}"
            )

            answer = None

        if answer is None:

            return self._fallback_answer(
                outputs
            )

        answer = str(
            answer
        ).strip()

        if not answer:

            return self._fallback_answer(
                outputs
            )

        return answer

    @staticmethod
    def _fallback_answer(
        outputs: dict[str, Any],
    ) -> str:

        if not outputs:
            return (
                "No usable task results were produced."
            )

        # Prefer final recommendation.
        preferred = (
            "recommend",
            "recommendation",
            "final",
            "answer",
            "synthesis",
            "compare",
            "evaluate",
        )

        for name in preferred:

            for task_id, value in outputs.items():

                if (
                    name
                    in str(task_id).lower()
                    and value
                ):

                    return str(
                        value
                    ).strip()

        # Last completed task.
        values = list(
            outputs.values()
        )

        for value in reversed(values):

            if value is not None and str(
                value
            ).strip():

                return str(
                    value
                ).strip()

        return (
            "No usable task results were produced."
        )

    # =========================================================
    # OUTPUT COLLECTION
    # =========================================================

    @staticmethod
    def _collect_outputs(
        graph,
    ) -> dict[str, Any]:

        outputs = {}

        nodes = getattr(
            graph,
            "nodes",
            {},
        )

        if not isinstance(
            nodes,
            dict,
        ):
            return outputs

        for node in nodes.values():

            output = getattr(
                node,
                "output_data",
                None,
            )

            if (
                output is not None
                and str(output).strip()
            ):

                outputs[
                    str(node.id)
                ] = output

        return outputs

    # =========================================================
    # REPAIR EXTRACTION
    # =========================================================

    @staticmethod
    def _extract_repairs(
        criticism,
    ) -> list:

        if criticism is None:
            return []

        if isinstance(
            criticism,
            dict,
        ):

            repairs = []

            for task_id, result in criticism.items():

                if not isinstance(
                    result,
                    dict,
                ):
                    continue

                status = str(
                    result.get(
                        "status",
                        "",
                    )
                ).lower()

                if status in {
                    "repair",
                    "repair_required",
                    "fail",
                }:

                    repairs.append(
                        (
                            task_id,
                            result,
                        )
                    )

            return repairs

        if isinstance(
            criticism,
            list,
        ):
            return criticism

        return []

    # =========================================================
    # PROGRESS
    # =========================================================

    def _get_progress(
        self,
        graph,
    ) -> dict[str, Any]:

        getter = getattr(
            self.executor,
            "get_progress",
            None,
        )

        if callable(getter):

            try:

                result = getter(
                    graph
                )

                if isinstance(
                    result,
                    dict,
                ) and "percentage" in result:

                    return result

            except Exception:
                pass

        nodes = getattr(
            graph,
            "nodes",
            {},
        )

        if not isinstance(
            nodes,
            dict,
        ):

            return {
                "total": 0,
                "completed": 0,
                "running": 0,
                "pending": 0,
                "failed": 0,
                "repairing": 0,
                "percentage": 100.0,
            }

        total = len(
            nodes
        )

        completed = 0
        running = 0
        pending = 0
        failed = 0
        repairing = 0

        for node in nodes.values():

            status = getattr(
                node,
                "status",
                None,
            )

            status = getattr(
                status,
                "value",
                status,
            )

            status = str(
                status
            ).lower()

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
            else 100.0
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
    # GRAPH STATUS
    # =========================================================

    @staticmethod
    def _all_tasks_completed(
        graph,
    ) -> bool:

        nodes = getattr(
            graph,
            "nodes",
            {},
        )

        if not nodes:
            return True

        if not isinstance(
            nodes,
            dict,
        ):
            return False

        for node in nodes.values():

            status = getattr(
                node,
                "status",
                None,
            )

            status = getattr(
                status,
                "value",
                status,
            )

            if str(
                status
            ).lower() != "completed":

                return False

        return True

    # =========================================================
    # GRAPH DISPLAY
    # =========================================================

    @staticmethod
    def _print_graph(
        graph,
    ) -> None:

        print()
        print(
            "[Engine] Planned DAG:"
        )

        nodes = getattr(
            graph,
            "nodes",
            {},
        )

        if not isinstance(
            nodes,
            dict,
        ):
            return

        for node in nodes.values():

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

            dependencies = (
                dependencies
                or []
            )

            dependency_text = (
                ", ".join(
                    str(item)
                    for item in dependencies
                )
                if dependencies
                else "none"
            )

            task_type = getattr(
                node,
                "task_type",
                "LLM",
            )

            task_type_text = getattr(
                task_type,
                "value",
                task_type,
            )

            print(
                f"  {node.id} "
                f"[{task_type_text}] "
                f"<- [{dependency_text}]"
            )

    # =========================================================
    # SHARED LLM STATUS
    # =========================================================

    def _shared_llm_enabled(
        self,
    ) -> bool:

        return (
            self._llm_client is not None
        )