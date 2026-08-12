"""
Runtime package for the autonomous multi-tool agent.

This package exposes the main AutonomousEngine without creating
an engine instance during package import.
"""

from .engine import AutonomousEngine

__all__ = [
    "AutonomousEngine",
]