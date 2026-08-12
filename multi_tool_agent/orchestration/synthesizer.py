from __future__ import annotations

from typing import Any


class Synthesizer:
    """
    Final user-facing answer generator.

    Rules:
        - Answer the ORIGINAL user request.
        - Never expose internal orchestration.
        - Keep answers concise.
        - Prefer recommendation/conclusion first.
        - Never return task-status text as the final answer.
    """

    def __init__(
        self,
        llm_client=None,
        max_words: int = 120,
    ) -> None:
        self.llm_client = llm_client
        self.max_words = max_words

    # =========================================================
    # PUBLIC API
    # =========================================================

    def synthesize(
        self,
        user_request: str,
        graph_or_outputs: Any,
    ) -> str:

        outputs = self._collect_outputs(
            graph_or_outputs
        )

        if not outputs:
            return (
                "I could not produce a usable answer."
            )

        # -----------------------------------------------------
        # LLM SYNTHESIS
        # -----------------------------------------------------

        if self.llm_client is not None:

            try:
                prompt = self._build_prompt(
                    user_request,
                    outputs,
                )

                answer = self.llm_client.generate(
                    system_prompt=self._system_prompt(),
                    user_prompt=prompt,
                )

                answer = self._clean_answer(
                    answer
                )

                # Reject bad fallback/status responses.
                if self._is_bad_answer(answer):
                    answer = ""

                if answer:
                    return self._limit_words(
                        answer
                    )

            except Exception as exc:
                print(
                    "[Synthesizer] "
                    f"LLM synthesis failed: {exc}"
                )

        # -----------------------------------------------------
        # FALLBACK
        # -----------------------------------------------------

        return self._fallback(
            outputs
        )

    # =========================================================
    # SYSTEM PROMPT
    # =========================================================

    def _system_prompt(self) -> str:
        return f"""
You are the final answer generator.

Answer ONLY the original user's request.

Rules:
- Give the answer directly.
- Put the conclusion/recommendation first when appropriate.
- Use concise paragraphs or bullets.
- Include only the strongest relevant facts.
- Do not mention internal tasks.
- Do not mention DAGs.
- Do not mention planners.
- Do not mention critics.
- Do not mention repairs.
- Do not mention replanning.
- Do not mention execution cycles.
- Do not mention autonomous orchestration.
- Do not say "Executed task".
- Do not say "No usable results".
- Do not describe how the answer was generated.

Maximum length: {self.max_words} words.

Return ONLY the final user-facing answer.
""".strip()

    # =========================================================
    # PROMPT
    # =========================================================

    def _build_prompt(
        self,
        user_request: str,
        outputs: dict[str, Any],
    ) -> str:

        parts = [
            "ORIGINAL USER REQUEST:",
            user_request.strip(),
            "",
            "AVAILABLE ANALYSIS:",
        ]

        for task_id, output in outputs.items():

            cleaned = self._clean_source_output(
                output
            )

            if not cleaned:
                continue

            parts.append(
                f"\n[{task_id}]"
            )

            parts.append(
                cleaned
            )

        parts.extend(
            [
                "",
                "FINAL ANSWER:",
                "",
                "Answer the ORIGINAL USER REQUEST.",
                "Do not discuss the internal analysis.",
                "If this is a comparison, state the winner clearly.",
                "If this is a recommendation, make a clear recommendation.",
                "Use only information supported by the analysis.",
                f"Keep the answer under {self.max_words} words.",
            ]
        )

        return "\n".join(parts)

    # =========================================================
    # COLLECT OUTPUTS
    # =========================================================

    @staticmethod
    def _collect_outputs(
        graph_or_outputs: Any,
    ) -> dict[str, Any]:

        if graph_or_outputs is None:
            return {}

        # Direct dictionary.
        if isinstance(
            graph_or_outputs,
            dict,
        ):
            return {
                str(key): value
                for key, value
                in graph_or_outputs.items()
                if Synthesizer._usable(value)
            }

        graph = graph_or_outputs

        nodes = getattr(
            graph,
            "nodes",
            {},
        )

        if isinstance(nodes, dict):
            iterable = nodes.values()
        else:
            iterable = nodes

        outputs: dict[str, Any] = {}

        for node in iterable:

            output = getattr(
                node,
                "output_data",
                None,
            )

            if not Synthesizer._usable(
                output
            ):
                continue

            node_id = getattr(
                node,
                "id",
                None,
            )

            if node_id is None:
                continue

            outputs[
                str(node_id)
            ] = output

        return outputs

    # =========================================================
    # VALIDATION
    # =========================================================

    @staticmethod
    def _usable(
        value: Any,
    ) -> bool:

        if value is None:
            return False

        if isinstance(
            value,
            str,
        ):
            text = value.strip()

            if not text:
                return False

            return not (
                text.startswith(
                    "Executed task:"
                )
                or
                text.startswith(
                    "No usable results"
                )
                or
                text.startswith(
                    "No usable task results"
                )
            )

        return True

    @staticmethod
    def _is_bad_answer(
        text: str,
    ) -> bool:

        if not text:
            return True

        lowered = text.lower().strip()

        bad_phrases = (
            "executed task:",
            "no usable results",
            "no usable task results",
            "i could not produce a usable",
            "i couldn't produce a usable",
        )

        return any(
            phrase in lowered
            for phrase in bad_phrases
        )

    # =========================================================
    # SOURCE CLEANING
    # =========================================================

    @staticmethod
    def _clean_source_output(
        output: Any,
    ) -> str:

        if output is None:
            return ""

        if isinstance(
            output,
            dict,
        ):
            # Prefer common answer fields.
            for key in (
                "answer",
                "result",
                "output",
                "content",
                "text",
                "response",
            ):
                value = output.get(key)

                if value:
                    return str(value).strip()

        return str(
            output
        ).strip()

    # =========================================================
    # ANSWER CLEANING
    # =========================================================

    @staticmethod
    def _clean_answer(
        answer: Any,
    ) -> str:

        if answer is None:
            return ""

        # Handle structured LLM responses.
        if isinstance(
            answer,
            dict,
        ):
            for key in (
                "answer",
                "result",
                "output",
                "content",
                "text",
                "response",
            ):
                value = answer.get(key)

                if value:
                    answer = value
                    break

        text = str(
            answer
        ).strip()

        if not text:
            return ""

        # Remove common wrappers.
        prefixes = (
            "FINAL ANSWER:",
            "Final Answer:",
            "Final answer:",
            "ANSWER:",
            "Answer:",
        )

        for prefix in prefixes:

            if text.startswith(prefix):
                text = text[
                    len(prefix):
                ].strip()

                break

        # Remove code fences.
        if text.startswith("```"):

            lines = text.splitlines()

            if (
                len(lines) >= 2
                and lines[-1].strip()
                == "```"
            ):
                text = "\n".join(
                    lines[1:-1]
                ).strip()

        return text

    # =========================================================
    # WORD LIMIT
    # =========================================================

    def _limit_words(
        self,
        text: str,
    ) -> str:

        words = text.split()

        if len(words) <= self.max_words:
            return text

        shortened = " ".join(
            words[: self.max_words]
        )

        # Prefer ending at punctuation.
        positions = []

        for punctuation in (
            ".",
            "!",
            "?",
        ):
            position = shortened.rfind(
                punctuation
            )

            if position >= 0:
                positions.append(
                    position
                )

        if positions:

            position = max(
                positions
            )

            if position >= int(
                len(shortened) * 0.70
            ):
                return shortened[
                    : position + 1
                ]

        return shortened + "..."

    # =========================================================
    # FALLBACK
    # =========================================================

    def _fallback(
        self,
        outputs: dict[str, Any],
    ) -> str:

        if not outputs:
            return (
                "I could not produce a usable answer."
            )

        # Prefer the final reasoning/recommendation.
        preferred = (
            "recommend",
            "recommendation",
            "final",
            "answer",
            "synthesis",
            "compare",
        )

        selected = None

        for preferred_key in preferred:

            for key, value in outputs.items():

                if (
                    preferred_key
                    in key.lower()
                    and self._usable(value)
                ):
                    selected = value
                    break

            if selected is not None:
                break

        # Otherwise use the last usable output.
        if selected is None:

            for value in reversed(
                list(outputs.values())
            ):
                if self._usable(value):
                    selected = value
                    break

        if selected is None:
            return (
                "I could not produce a usable answer."
            )

        text = self._clean_source_output(
            selected
        )

        text = self._clean_answer(
            text
        )

        if self._is_bad_answer(text):
            return (
                "I could not produce a usable answer."
            )

        return self._limit_words(
            text
        )