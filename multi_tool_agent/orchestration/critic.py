from __future__ import annotations

import json
from typing import Any

from ..llm_client import LLMClient


class Critic:
    """
    Production-quality task critic.

    Evaluates completed TaskNodes and returns:

        9-10 -> pass
        7-8  -> pass_with_warning
        0-6  -> repair
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
    ) -> None:

        self.llm = (
            llm_client
            or LLMClient()
        )

    # =========================================================
    # PUBLIC API
    # =========================================================

    def evaluate_completed(
        self,
        graph: Any,
        state: Any = None,
    ) -> dict[str, dict]:

        results: dict[str, dict] = {}

        nodes = getattr(
            graph,
            "nodes",
            None,
        )

        if nodes is None:

            raise TypeError(
                "Critic expected TaskGraph.nodes."
            )

        if isinstance(
            nodes,
            dict,
        ):

            node_list = list(
                nodes.values()
            )

        else:

            node_list = list(nodes)

        for node in node_list:

            status = getattr(
                node,
                "status",
                None,
            )

            status_value = getattr(
                status,
                "value",
                str(status),
            )

            if status_value != "completed":
                continue

            results[
                node.id
            ] = self.evaluate(node)

        return results

    # =========================================================
    # SINGLE TASK EVALUATION
    # =========================================================

    def evaluate(
        self,
        node: Any,
    ) -> dict:

        print(
            f"\n[Critic] Evaluating: {node.id}"
        )

        output = getattr(
            node,
            "output_data",
            None,
        )

        # -----------------------------------------------------
        # Missing output
        # -----------------------------------------------------

        if (
            output is None
            or not str(output).strip()
        ):

            result = {
                "status": "repair",
                "score": 0,
                "issues": [
                    {
                        "type": "missing_output",
                        "description": (
                            "The task completed without "
                            "producing usable output."
                        ),
                    }
                ],
                "repair_instructions": [
                    {
                        "type": "retry",
                        "description": (
                            "Execute the task again and "
                            "produce meaningful output."
                        ),
                    }
                ],
                "reason": (
                    "No usable output was produced."
                ),
            }

            print(
                "[Critic] REPAIR REQUIRED: "
                f"{node.id} (score=0)"
            )

            return result

        # -----------------------------------------------------
        # Build evaluation prompt
        # -----------------------------------------------------

        prompt = f"""
You are the quality-control critic of an autonomous AI agent.

Evaluate the completed task below.

TASK ID:
{node.id}

TASK:
{node.task}

OUTPUT:
{output}

Return ONLY valid JSON.

Required structure:

{{
    "score": 0,
    "issues": [],
    "repair_instructions": [],
    "reason": ""
}}

SCORING:

9-10:
Excellent and fully usable.

7-8:
Good enough to continue.
Minor imperfections are acceptable.
Do not request repair merely because additional detail
could improve the answer.

5-6:
Meaningful problems exist.
Repair is recommended.

0-4:
Major failure.
Repair is required.

Evaluate:

1. Correctness
2. Relevance
3. Completeness
4. Internal consistency
5. Whether the output satisfies the task

IMPORTANT:

Do not invent requirements.

Do not demand external sources unless the task explicitly
requires sources.

Do not demand perfect formatting.

Do not request additional research merely because more
research could improve the answer.

The task should only be marked for repair when there is
a meaningful problem with the actual output.
""".strip()

        # -----------------------------------------------------
        # LLM evaluation
        # -----------------------------------------------------

        try:

            raw = self.llm.generate(
                system_prompt=(
                    "You are a strict but fair quality "
                    "control evaluator. Return valid JSON "
                    "only."
                ),
                user_prompt=prompt,
            )

            result = self._parse_result(
                raw
            )

        except Exception as exc:

            print(
                "[Critic] Evaluation error: "
                f"{exc}"
            )

            # Fail-open.
            #
            # A temporary critic failure must not destroy
            # an otherwise successful autonomous execution.

            result = {
                "score": 7,
                "issues": [
                    {
                        "type": "critic_error",
                        "description": str(exc),
                    }
                ],
                "repair_instructions": [],
                "reason": (
                    "Critic evaluation failed; "
                    "task allowed to continue."
                ),
            }

        # -----------------------------------------------------
        # Normalize
        # -----------------------------------------------------

        score = self._normalize_score(
            result.get(
                "score",
                0,
            )
        )

        result["score"] = score

        result["status"] = (
            self._decision(score)
        )

        result.setdefault(
            "issues",
            [],
        )

        result.setdefault(
            "repair_instructions",
            [],
        )

        result.setdefault(
            "reason",
            "",
        )

        # -----------------------------------------------------
        # Logging
        # -----------------------------------------------------

        if result["status"] == "pass":

            print(
                f"[Critic] PASS: {node.id} "
                f"(score={score})"
            )

        elif (
            result["status"]
            == "pass_with_warning"
        ):

            print(
                "[Critic] PASS WITH WARNING: "
                f"{node.id} (score={score})"
            )

        else:

            print(
                "[Critic] REPAIR REQUIRED: "
                f"{node.id} (score={score})"
            )

            for issue in result.get(
                "issues",
                [],
            ):

                if isinstance(
                    issue,
                    dict,
                ):

                    description = issue.get(
                        "description",
                        "Unknown issue",
                    )

                else:

                    description = str(
                        issue
                    )

                print(
                    f"  - {description}"
                )

        return result

    # =========================================================
    # DECISION
    # =========================================================

    @staticmethod
    def _decision(
        score: int,
    ) -> str:

        if score >= 9:
            return "pass"

        if score >= 7:
            return "pass_with_warning"

        return "repair"

    # =========================================================
    # SCORE NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize_score(
        score: Any,
    ) -> int:

        try:

            score = int(
                float(score)
            )

        except (
            TypeError,
            ValueError,
        ):

            score = 0

        return max(
            0,
            min(
                10,
                score,
            ),
        )

    # =========================================================
    # JSON PARSER
    # =========================================================

    @staticmethod
    def _parse_result(
        raw: Any,
    ) -> dict:

        if isinstance(
            raw,
            dict,
        ):

            result = raw

        else:

            text = str(
                raw
            ).strip()

            # ---------------------------------------------
            # Remove markdown code fences
            # ---------------------------------------------

            if text.startswith(
                "```"
            ):

                lines = (
                    text.splitlines()
                )

                if (
                    lines
                    and lines[0].startswith(
                        "```"
                    )
                ):

                    lines = lines[1:]

                if (
                    lines
                    and lines[-1].strip()
                    == "```"
                ):

                    lines = lines[:-1]

                text = "\n".join(
                    lines
                ).strip()

            # ---------------------------------------------
            # Remove "json" prefix
            # ---------------------------------------------

            if text.lower().startswith(
                "json"
            ):

                text = text[4:].strip()

            # ---------------------------------------------
            # Try direct JSON
            # ---------------------------------------------

            try:

                result = json.loads(
                    text
                )

            except json.JSONDecodeError:

                # -----------------------------------------
                # Recover JSON object embedded in text
                # -----------------------------------------

                start = text.find(
                    "{"
                )

                end = text.rfind(
                    "}"
                )

                if (
                    start >= 0
                    and end > start
                ):

                    result = json.loads(
                        text[
                            start:
                            end + 1
                        ]
                    )

                else:

                    raise ValueError(
                        "Critic returned invalid JSON."
                    )

        if not isinstance(
            result,
            dict,
        ):

            raise ValueError(
                "Critic returned invalid "
                "JSON structure."
            )

        result.setdefault(
            "score",
            0,
        )

        result.setdefault(
            "issues",
            [],
        )

        result.setdefault(
            "repair_instructions",
            [],
        )

        result.setdefault(
            "reason",
            "",
        )

        return result