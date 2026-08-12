from __future__ import annotations

from dataclasses import dataclass

from .config import get_available_providers


@dataclass(frozen=True)
class ModelOption:
    provider: str
    model: str
    capability: str
    speed: int
    quality: int
    cost_efficiency: int

    @property
    def score(self) -> float:
        return (
            self.quality * 0.45
            + self.speed * 0.25
            + self.cost_efficiency * 0.30
        )


# ============================================================
# MODEL REGISTRY
# ============================================================
#
# These are your currently selected defaults.
#
# The important architectural point is that the provider is
# independent from the autonomous engine.
#
# You can change models here without touching:
#
# Router
# Planner
# Executor
# Critic
# Replanner
# Synthesizer
# Tools
# Runtime
#
# ============================================================

MODEL_OPTIONS: dict[str, list[ModelOption]] = {

    "openai": [
        ModelOption(
            provider="openai",
            model="gpt-4o-mini",
            capability="general",
            speed=9,
            quality=8,
            cost_efficiency=9,
        ),
    ],

    "gemini": [
        ModelOption(
            provider="gemini",
            model="gemini-2.0-flash",
            capability="general",
            speed=9,
            quality=8,
            cost_efficiency=9,
        ),
    ],

    "nvidia_nim": [
        ModelOption(
            provider="nvidia_nim",
            model="meta/llama-3.1-8b-instruct",
            capability="general",
            speed=9,
            quality=7,
            cost_efficiency=9,
        ),
    ],

    "huggingface": [
        ModelOption(
            provider="huggingface",
            model="HuggingFaceH4/zephyr-7b-beta",
            capability="general",
            speed=7,
            quality=6,
            cost_efficiency=9,
        ),
    ],

    "xai": [
        ModelOption(
            provider="xai",
            model="grok-2-latest",
            capability="general",
            speed=8,
            quality=8,
            cost_efficiency=7,
        ),
    ],

    "anthropic": [
        ModelOption(
            provider="anthropic",
            model="claude-3-5-haiku-latest",
            capability="general",
            speed=9,
            quality=8,
            cost_efficiency=8,
        ),
    ],

    "deepseek": [
        ModelOption(
            provider="deepseek",
            model="deepseek-chat",
            capability="general",
            speed=8,
            quality=8,
            cost_efficiency=9,
        ),
    ],
}


def get_candidates() -> list[ModelOption]:
    """
    Return models belonging only to configured providers.
    """

    available = get_available_providers()

    candidates: list[ModelOption] = []

    for provider in available:

        candidates.extend(
            MODEL_OPTIONS.get(
                provider,
                [],
            )
        )

    return candidates


def choose_model() -> ModelOption:
    """
    Select the highest scoring available model.
    """

    candidates = get_candidates()

    if not candidates:

        raise RuntimeError(
            "No supported provider API key was found. "
            "Configure at least one provider in .env."
        )

    return max(
        candidates,
        key=lambda model: model.score,
    )


def get_ranked_candidates() -> list[ModelOption]:
    """
    Return all available models ordered by score.

    This is what the failover system uses.
    """

    candidates = get_candidates()

    return sorted(
        candidates,
        key=lambda model: model.score,
        reverse=True,
    )


def print_model_status() -> None:

    candidates = get_ranked_candidates()

    print(
        "\n============================================================"
    )

    print("AVAILABLE LLM PROVIDERS")

    print(
        "============================================================"
    )

    if not candidates:

        print("No providers configured.")

        return

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):

        print(
            f"{index}. "
            f"{candidate.provider} / "
            f"{candidate.model} "
            f"(score={candidate.score:.2f})"
        )

    selected = candidates[0]

    print(
        "\nPrimary:"
    )

    print(
        f"  {selected.provider} / {selected.model}"
    )


if __name__ == "__main__":

    print_model_status()