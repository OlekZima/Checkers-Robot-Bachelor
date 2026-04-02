"""Decision engine exceptions."""

from __future__ import annotations

__all__ = [
    "DecisionEngineError",
]


class DecisionEngineError(Exception):
    """Raised when the AI decision engine encounters an invalid state or criteria."""
