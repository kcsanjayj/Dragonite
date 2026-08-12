from __future__ import annotations

from .runtime.engine import AutonomousEngine


# ============================================================
# SINGLETON AUTONOMOUS ENGINE
# ============================================================

_engine: AutonomousEngine | None = None


def get_engine() -> AutonomousEngine:
    """
    Return the single application-wide AutonomousEngine.

    The engine is created lazily, so importing this module does
    not immediately construct the complete LLM/planner stack.
    """

    global _engine

    if _engine is None:
        _engine = AutonomousEngine()

    return _engine


# ============================================================
# DIRECT APPLICATION API
# ============================================================

def run_agent(request: str) -> str:
    """
    Main application entry point.
    """

    if not request or not request.strip():
        return "Please provide a request."

    engine = get_engine()

    result = engine.run(
        request.strip()
    )

    if isinstance(result, dict):

        answer = result.get(
            "answer",
            "",
        )

        if answer:
            return str(answer)

        return str(result)

    return str(result)


# ============================================================
# ADK ROOT ENTRYPOINT
# ============================================================
#
# IMPORTANT:
#
# The AutonomousEngine remains the real orchestration brain.
#
# ADK
#   ↓
# run_agent()
#   ↓
# AutonomousEngine
#   ↓
# Memory
#   ↓
# Planner
#   ↓
# Multi-provider LLM
#   ↓
# DAG Executor
#   ↓
# Tools
#   ↓
# Critic
#   ↓
# Replanner
#   ↓
# Synthesis
#
# No Gemini-only model is introduced here.
#

root_agent = get_engine()