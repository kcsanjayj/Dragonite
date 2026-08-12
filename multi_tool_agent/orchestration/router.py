from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..llm_client import LLMClient


@dataclass
class RouteDecision:
    category: str
    complexity: str
    needs_research: bool
    needs_parallel_execution: bool
    needs_criticism: bool
    needs_replanning: bool
    reasoning: str


class Router:
    """
    Intelligent request router.

    The Router does NOT solve the request.

    Its job is to determine:
        1. What kind of request is this?
        2. How complex is it?
        3. Does it require research?
        4. Should tasks run in parallel?
        5. Should results be critically checked?
        6. Should autonomous repair be enabled?
    """

    VALID_CATEGORIES = {
        "general",
        "question_answering",
        "coding",
        "debugging",
        "research",
        "comparison",
        "analysis",
        "planning",
        "creative",
        "complex",
    }

    VALID_COMPLEXITIES = {
        "simple",
        "moderate",
        "complex",
    }

    def __init__(self) -> None:
        self.llm = LLMClient()

    # ---------------------------------------------------------
    # Main routing method
    # ---------------------------------------------------------

    def route(self, user_request: str) -> RouteDecision:
        """
        Analyze a user request and produce a routing decision.
        """

        if not user_request or not user_request.strip():
            raise ValueError(
                "user_request cannot be empty."
            )

        print()
        print("[Router] Analyzing request...")

        prompt = f"""
You are the routing intelligence of an autonomous AI agent.

Analyze the following user request:

USER REQUEST:
{user_request}

Classify it.

Choose exactly ONE category:

general
question_answering
coding
debugging
research
comparison
analysis
planning
creative
complex

Choose exactly ONE complexity:

simple
moderate
complex

Then determine:

needs_research:
true or false

needs_parallel_execution:
true or false

needs_criticism:
true or false

needs_replanning:
true or false

Return ONLY valid JSON.

Required format:

{{
  "category": "comparison",
  "complexity": "moderate",
  "needs_research": true,
  "needs_parallel_execution": true,
  "needs_criticism": true,
  "needs_replanning": true,
  "reasoning": "Short explanation."
}}
"""

        try:
            response = self.llm.generate(
                system_prompt=(
                    "You are an intelligent request "
                    "classification router."
                ),
                user_prompt=prompt,
            )

            decision = self._parse_response(response)

        except Exception as exc:
            print(
                f"[Router] LLM routing failed: {exc}"
            )

            # Safe fallback.
            decision = self._fallback_route(
                user_request
            )

        self._print_decision(decision)

        return decision

    # ---------------------------------------------------------
    # Parse LLM response
    # ---------------------------------------------------------

    def _parse_response(
        self,
        response: Any,
    ) -> RouteDecision:

        if not isinstance(response, str):
            response = str(response)

        text = response.strip()

        # Remove markdown JSON fences if the model adds them.
        if text.startswith("```"):
            lines = text.splitlines()

            if lines:
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            text = "\n".join(lines).strip()

        import json

        data = json.loads(text)

        category = str(
            data.get(
                "category",
                "general",
            )
        ).lower().strip()

        complexity = str(
            data.get(
                "complexity",
                "moderate",
            )
        ).lower().strip()

        if category not in self.VALID_CATEGORIES:
            category = "general"

        if complexity not in self.VALID_COMPLEXITIES:
            complexity = "moderate"

        return RouteDecision(
            category=category,
            complexity=complexity,
            needs_research=bool(
                data.get(
                    "needs_research",
                    False,
                )
            ),
            needs_parallel_execution=bool(
                data.get(
                    "needs_parallel_execution",
                    False,
                )
            ),
            needs_criticism=bool(
                data.get(
                    "needs_criticism",
                    True,
                )
            ),
            needs_replanning=bool(
                data.get(
                    "needs_replanning",
                    True,
                )
            ),
            reasoning=str(
                data.get(
                    "reasoning",
                    "",
                )
            ),
        )

    # ---------------------------------------------------------
    # Fallback routing
    # ---------------------------------------------------------

    def _fallback_route(
        self,
        user_request: str,
    ) -> RouteDecision:

        text = user_request.lower()

        # Coding
        coding_words = {
            "code",
            "python",
            "javascript",
            "typescript",
            "rust",
            "java",
            "api",
            "function",
            "program",
            "implement",
            "build",
        }

        if any(
            word in text
            for word in coding_words
        ):
            category = "coding"

        # Debugging
        elif any(
            word in text
            for word in {
                "error",
                "exception",
                "traceback",
                "bug",
                "broken",
                "debug",
                "not working",
            }
        ):
            category = "debugging"

        # Comparison
        elif any(
            word in text
            for word in {
                "compare",
                "comparison",
                "versus",
                " vs ",
                "better",
                "difference",
                "which one",
            }
        ):
            category = "comparison"

        # Research
        elif any(
            word in text
            for word in {
                "research",
                "investigate",
                "latest",
                "find",
                "sources",
                "study",
            }
        ):
            category = "research"

        # Planning
        elif any(
            word in text
            for word in {
                "plan",
                "roadmap",
                "strategy",
                "steps",
                "architecture",
            }
        ):
            category = "planning"

        else:
            category = "general"

        word_count = len(text.split())

        if word_count < 15:
            complexity = "simple"
        elif word_count < 50:
            complexity = "moderate"
        else:
            complexity = "complex"

        complex_request = (
            complexity == "complex"
            or category in {
                "research",
                "comparison",
                "analysis",
                "planning",
                "complex",
            }
        )

        return RouteDecision(
            category=category,
            complexity=complexity,
            needs_research=category in {
                "research",
                "comparison",
                "analysis",
            },
            needs_parallel_execution=complex_request,
            needs_criticism=complex_request,
            needs_replanning=complex_request,
            reasoning=(
                "Fallback rule-based routing was used "
                "because LLM routing was unavailable."
            ),
        )

    # ---------------------------------------------------------
    # Display
    # ---------------------------------------------------------

    @staticmethod
    def _print_decision(
        decision: RouteDecision,
    ) -> None:

        print()
        print("[Router] Decision")
        print(
            f"  Category                 : "
            f"{decision.category}"
        )
        print(
            f"  Complexity               : "
            f"{decision.complexity}"
        )
        print(
            f"  Needs research           : "
            f"{decision.needs_research}"
        )
        print(
            f"  Parallel execution       : "
            f"{decision.needs_parallel_execution}"
        )
        print(
            f"  Criticism                : "
            f"{decision.needs_criticism}"
        )
        print(
            f"  Replanning               : "
            f"{decision.needs_replanning}"
        )
        print(
            f"  Reasoning                : "
            f"{decision.reasoning}"
        )


if __name__ == "__main__":

    router = Router()

    tests = [
        "Explain recursion in Python.",
        "Compare Python and Rust for a high-performance API.",
        "Debug this Python traceback.",
        "Research the best database for a large-scale application.",
        "Create a production architecture for an AI platform.",
    ]

    print()
    print("=" * 60)
    print("ROUTER TEST")
    print("=" * 60)

    for request in tests:

        print()
        print("-" * 60)
        print(f"Request: {request}")

        decision = router.route(request)

        print(
            f"Result: "
            f"{decision.category} / "
            f"{decision.complexity}"
        )

    print()
    print("=" * 60)
    print("ROUTER TEST COMPLETE")
    print("=" * 60)