"""
Error definitions for the autonomous agent system.
Custom exception classes.
"""


class DragonError(Exception):
    """Base exception for Dragon."""
    pass


class PlanValidationError(DragonError):
    """Raised when plan validation fails."""
    pass


class ExecutionError(DragonError):
    """Raised when execution fails."""
    pass


class ToolExecutionError(DragonError):
    """Raised when tool execution fails."""
    pass


class LLMError(DragonError):
    """Raised when LLM interaction fails."""
    pass


class ConfigurationError(DragonError):
    """Raised when configuration is invalid."""
    pass


class RecoveryError(DragonError):
    """Raised when recovery fails."""
    pass