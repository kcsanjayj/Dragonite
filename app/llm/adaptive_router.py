"""
Adaptive model selection for intelligent LLM routing.
Routes requests to appropriate providers based on task complexity and failure history.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"      # Quick queries, simple tasks
    MODERATE = "moderate"  # Standard tasks
    COMPLEX = "complex"    # Multi-step reasoning, analysis
    CRITICAL = "critical"  # High-stakes, requires best model


@dataclass
class ProviderInfo:
    """Information about an LLM provider."""
    name: str
    cost_tier: str  # cheap, moderate, expensive
    strength: str   # general, reasoning, coding, etc.
    failure_count: int = 0
    success_count: int = 0


class AdaptiveModelRouter:
    """
    Intelligent router for selecting LLM providers.
    Considers task type, complexity, cost, and failure history.
    """

    def __init__(self):
        """Initialize the adaptive router."""
        self.providers: Dict[str, ProviderInfo] = {
            "gemini": ProviderInfo("gemini", "cheap", "general"),
            "openai": ProviderInfo("openai", "moderate", "general"),
            "anthropic": ProviderInfo("anthropic", "expensive", "reasoning"),
            "nvidia": ProviderInfo("nvidia", "moderate", "coding"),
        }
        self._current_provider: Optional[str] = None

    def select_provider(
        self,
        task_type: str,
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        previous_attempt_failed: bool = False,
        preferred_provider: Optional[str] = None
    ) -> str:
        """
        Select the best provider for a task.

        Args:
            task_type: Type of task (planning, routing, synthesis, etc.)
            complexity: Task complexity level
            previous_attempt_failed: Whether previous attempt with current provider failed
            preferred_provider: User-preferred provider if any

        Returns:
            Selected provider name
        """
        # If preferred provider specified and not failing, use it
        if preferred_provider and preferred_provider in self.providers:
            provider_info = self.providers[preferred_provider]
            if provider_info.failure_count < 3:  # Not in failure spiral
                return preferred_provider

        # If previous attempt failed, switch provider
        if previous_attempt_failed and self._current_provider:
            return self._failover_provider(self._current_provider)

        # Route based on task characteristics
        if complexity == TaskComplexity.SIMPLE:
            return self._select_cheapest_available()

        elif complexity == TaskComplexity.COMPLEX:
            return self._select_best_quality()

        elif complexity == TaskComplexity.CRITICAL:
            return self._select_most_reliable()

        else:  # MODERATE
            return self._select_balanced(task_type)

    def _select_cheapest_available(self) -> str:
        """Select the cheapest provider that's not failing."""
        cheap_providers = ["gemini", "openai"]  # Ordered by cost
        for provider in cheap_providers:
            if self.providers[provider].failure_count < 3:
                return provider
        return "openai"  # Default fallback

    def _select_best_quality(self) -> str:
        """Select provider with best quality (for complex tasks)."""
        # Anthropic for reasoning, NVIDIA for coding
        quality_providers = ["anthropic", "nvidia", "openai"]
        for provider in quality_providers:
            if self.providers[provider].failure_count < 2:
                return provider
        return "openai"

    def _select_most_reliable(self) -> str:
        """Select the most reliable provider (for critical tasks)."""
        # Sort by success rate
        sorted_providers = sorted(
            self.providers.items(),
            key=lambda x: x[1].success_count / max(x[1].success_count + x[1].failure_count, 1),
            reverse=True
        )
        return sorted_providers[0][0] if sorted_providers else "openai"

    def _select_balanced(self, task_type: str) -> str:
        """Select balanced provider based on task type."""
        task_routing = {
            "planning": "anthropic",      # Complex reasoning
            "routing": "gemini",          # Simple classification
            "synthesis": "openai",        # Good at writing
            "critic": "anthropic",        # Critical evaluation
            "replanning": "anthropic",    # Complex repair
            "code": "nvidia",             # Code tasks
            "default": "openai"
        }
        return task_routing.get(task_type, "openai")

    def _failover_provider(self, current: str) -> str:
        """Select failover provider when current is failing."""
        failover_map = {
            "openai": "anthropic",
            "anthropic": "nvidia",
            "nvidia": "openai",
            "gemini": "openai"
        }
        return failover_map.get(current, "openai")

    def record_success(self, provider: str) -> None:
        """Record successful execution."""
        if provider in self.providers:
            self.providers[provider].success_count += 1

    def record_failure(self, provider: str) -> None:
        """Record failed execution."""
        if provider in self.providers:
            self.providers[provider].failure_count += 1

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get routing statistics."""
        return {
            name: {
                "success_count": info.success_count,
                "failure_count": info.failure_count,
                "success_rate": info.success_count / max(info.success_count + info.failure_count, 1),
                "cost_tier": info.cost_tier,
                "strength": info.strength
            }
            for name, info in self.providers.items()
        }

    def reset_stats(self) -> None:
        """Reset all provider statistics."""
        for provider in self.providers.values():
            provider.success_count = 0
            provider.failure_count = 0


# Global adaptive router instance
adaptive_router = AdaptiveModelRouter()
