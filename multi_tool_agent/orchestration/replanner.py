from __future__ import annotations

from typing import Any


class Replanner:
    """
    Repairs failed or low-quality tasks in the autonomous DAG.

    Important design rule:

        The original node.task is NEVER replaced.

    Repair instructions are stored separately in node.metadata so
    the Executor can use them while preserving the original objective.
    """

    def __init__(
        self,
        max_repairs: int = 2,
    ) -> None:

        self.max_repairs = max(
            1,
            int(max_repairs),
        )

    # =========================================================
    # PUBLIC API
    # =========================================================

    def repair(
        self,
        graph: Any,
        criticism: Any,
    ) -> dict[str, Any]:
        """
        Repair tasks identified by the Critic.

        The original task remains unchanged.
        Repair instructions are stored in metadata.
        """

        print()
        print("[Replanner] Starting repair analysis...")

        if graph is None:
            raise ValueError(
                "Replanner received graph=None."
            )

        nodes = getattr(
            graph,
            "nodes",
            None,
        )

        if nodes is None:
            raise TypeError(
                "Replanner expected TaskGraph.nodes."
            )

        repairs = self._extract_repairs(
            criticism
        )

        if not repairs:

            print(
                "[Replanner] No repair-required "
                "tasks found."
            )

            return {
                "repaired": [],
                "skipped": [],
                "failed": [],
                "count": 0,
            }

        repaired = []
        skipped = []
        failed = []

        for task_id, result in repairs:

            node = self._get_node(
                nodes,
                task_id,
            )

            if node is None:

                print(
                    f"[Replanner] Task not found: "
                    f"{task_id}"
                )

                failed.append(
                    {
                        "task_id": task_id,
                        "reason": (
                            "Task does not exist "
                            "in graph."
                        ),
                    }
                )

                continue

            print()
            print(
                f"[Replanner] Repairing: "
                f"{task_id}"
            )

            # =================================================
            # REPAIR LIMIT
            # =================================================

            repair_count = self._get_repair_count(
                node
            )

            if repair_count >= self.max_repairs:

                print(
                    f"[Replanner] Repair limit "
                    f"reached: {task_id}"
                )

                skipped.append(
                    {
                        "task_id": task_id,
                        "reason": (
                            "Maximum repair attempts "
                            "reached."
                        ),
                    }
                )

                continue

            # =================================================
            # PRESERVE CRITIC INFORMATION
            # =================================================

            repair_instructions = []

            if isinstance(
                result,
                dict,
            ):

                repair_instructions = (
                    result.get(
                        "repair_instructions",
                        [],
                    )
                )

            # =================================================
            # STORE REPAIR METADATA
            # =================================================

            metadata = getattr(
                node,
                "metadata",
                None,
            )

            if metadata is None:

                metadata = {}

                try:
                    node.metadata = metadata
                except Exception:
                    pass

            if not isinstance(
                metadata,
                dict,
            ):

                metadata = {}

                try:
                    node.metadata = metadata
                except Exception:
                    pass

            metadata["repair_count"] = (
                repair_count + 1
            )

            metadata["last_criticism"] = result

            metadata["repair_instructions"] = (
                repair_instructions
            )

            # Preserve the original task explicitly.
            original_task = getattr(
                node,
                "task",
                "",
            )

            metadata["original_task"] = (
                original_task
            )

            # =================================================
            # IMPORTANT:
            #
            # DO NOT MODIFY node.task
            #
            # The previous implementation did:
            #
            #     node.task = improved_task
            #
            # That caused the Executor to answer the repair
            # instruction instead of the original task.
            # =================================================

            print(
                "[Replanner] Original task preserved."
            )

            # =================================================
            # RESET EXECUTION STATE
            # =================================================

            self._reset_for_retry(
                node
            )

            repaired.append(
                {
                    "task_id": task_id,
                    "repair_count": (
                        repair_count + 1
                    ),
                    "instructions": (
                        repair_instructions
                    ),
                }
            )

            print(
                f"[Replanner] Repair prepared: "
                f"{task_id}"
            )

        result = {
            "repaired": repaired,
            "skipped": skipped,
            "failed": failed,
            "count": len(repaired),
        }

        print()
        print(
            "[Replanner] Repair summary:"
        )

        print(
            f"  Repaired: {len(repaired)}"
        )

        print(
            f"  Skipped:  {len(skipped)}"
        )

        print(
            f"  Failed:   {len(failed)}"
        )

        return result

    # =========================================================
    # CRITIC PARSING
    # =========================================================

    @staticmethod
    def _extract_repairs(
        criticism: Any,
    ) -> list[tuple[str, Any]]:

        if criticism is None:
            return []

        # -----------------------------------------------------
        # Dict format
        # -----------------------------------------------------

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
                    "failed",
                }:

                    repairs.append(
                        (
                            task_id,
                            result,
                        )
                    )

            return repairs

        # -----------------------------------------------------
        # List format
        # -----------------------------------------------------

        if isinstance(
            criticism,
            list,
        ):

            repairs = []

            for item in criticism:

                if isinstance(
                    item,
                    tuple,
                ) and len(item) >= 2:

                    repairs.append(
                        (
                            item[0],
                            item[1],
                        )
                    )

                    continue

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                task_id = item.get(
                    "task_id"
                )

                if not task_id:
                    continue

                status = str(
                    item.get(
                        "status",
                        "repair",
                    )
                ).lower()

                if status in {
                    "repair",
                    "repair_required",
                    "fail",
                    "failed",
                }:

                    repairs.append(
                        (
                            task_id,
                            item,
                        )
                    )

            return repairs

        return []

    # =========================================================
    # NODE LOOKUP
    # =========================================================

    @staticmethod
    def _get_node(
        nodes: Any,
        task_id: str,
    ) -> Any:

        if isinstance(
            nodes,
            dict,
        ):

            return nodes.get(
                task_id
            )

        for node in nodes:

            if getattr(
                node,
                "id",
                None,
            ) == task_id:

                return node

        return None

    # =========================================================
    # REPAIR COUNT
    # =========================================================

    @staticmethod
    def _get_repair_count(
        node: Any,
    ) -> int:

        metadata = getattr(
            node,
            "metadata",
            {},
        )

        if not isinstance(
            metadata,
            dict,
        ):
            return 0

        value = metadata.get(
            "repair_count",
            0,
        )

        try:

            return max(
                0,
                int(value),
            )

        except (
            TypeError,
            ValueError,
        ):

            return 0

    # =========================================================
    # RESET NODE
    # =========================================================

    @staticmethod
    def _reset_for_retry(
        node: Any,
    ) -> None:

        # Prefer TaskNode.prepare_retry()
        # when available.

        prepare_retry = getattr(
            node,
            "prepare_retry",
            None,
        )

        if callable(
            prepare_retry
        ):

            prepare_retry()
            return

        # -----------------------------------------------------
        # Compatibility fallback
        # -----------------------------------------------------

        try:

            from multi_tool_agent.core.node import (
                NodeStatus,
            )

            node.status = (
                NodeStatus.PENDING
            )

        except Exception:

            try:
                node.status = "pending"
            except Exception:
                pass

        try:
            node.error = None
        except Exception:
            pass

        try:
            node.output_data = None
        except Exception:
            pass

    # =========================================================
    # OPTIONAL COMPATIBILITY API
    # =========================================================

    def replan(
        self,
        graph: Any,
        criticism: Any,
    ) -> dict[str, Any]:
        """
        Compatibility alias.

        Older engine versions may call replan()
        instead of repair().
        """

        return self.repair(
            graph,
            criticism,
        )