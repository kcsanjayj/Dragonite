"""
Circuit breaker pattern for tool execution backpressure.
Prevents burning tokens on failing tools/environments.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker for tool execution.
    Opens after threshold failures, preventing cascade failures.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 2
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Tool/service name
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            half_open_max_calls: Max test calls in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        # Check if we should transition from OPEN to HALF_OPEN
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0

        return self._state

    def is_open(self) -> bool:
        """
        Check if circuit is open (failing).

        Returns:
            True if circuit is open and calls should be rejected
        """
        return self.state == CircuitState.OPEN

    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    def can_execute(self) -> bool:
        """
        Check if execution is allowed.

        Returns:
            True if call should proceed
        """
        current_state = self.state  # Triggers state transition check

        if current_state == CircuitState.OPEN:
            return False

        if current_state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                return False
            self._half_open_calls += 1

        return True

    def record_success(self) -> None:
        """Record successful execution."""
        if self._state == CircuitState.HALF_OPEN:
            # Recovery successful, close circuit
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record failed execution."""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()

        if self._state == CircuitState.HALF_OPEN:
            # Recovery failed, open circuit again
            self._state = CircuitState.OPEN
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                # Too many failures, open circuit
                self._state = CircuitState.OPEN

    def get_stats(self) -> Dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }


class CircuitBreakerRegistry:
    """Registry for managing circuit breakers per tool."""

    def __init__(self):
        """Initialize circuit breaker registry."""
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_threshold = 3
        self._default_timeout = 60

    def get_breaker(self, tool_name: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for tool.

        Args:
            tool_name: Name of the tool

        Returns:
            CircuitBreaker instance
        """
        if tool_name not in self._breakers:
            self._breakers[tool_name] = CircuitBreaker(
                name=tool_name,
                failure_threshold=self._default_threshold,
                recovery_timeout=self._default_timeout
            )
        return self._breakers[tool_name]

    def record_success(self, tool_name: str) -> None:
        """Record success for a tool."""
        breaker = self.get_breaker(tool_name)
        breaker.record_success()

    def record_failure(self, tool_name: str) -> None:
        """Record failure for a tool."""
        breaker = self.get_breaker(tool_name)
        breaker.record_failure()

    def is_open(self, tool_name: str) -> bool:
        """Check if circuit is open for a tool."""
        return self.get_breaker(tool_name).is_open()

    def can_execute(self, tool_name: str) -> bool:
        """Check if tool execution is allowed."""
        return self.get_breaker(tool_name).can_execute()

    def get_all_stats(self) -> Dict[str, Dict]:
        """Get stats for all circuit breakers."""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    def reset(self, tool_name: Optional[str] = None) -> None:
        """
        Reset circuit breaker(s).

        Args:
            tool_name: If specified, reset only this tool. Otherwise reset all.
        """
        if tool_name:
            if tool_name in self._breakers:
                self._breakers[tool_name] = CircuitBreaker(
                    name=tool_name,
                    failure_threshold=self._default_threshold,
                    recovery_timeout=self._default_timeout
                )
        else:
            self._breakers.clear()


# Global circuit breaker registry
circuit_breakers = CircuitBreakerRegistry()
