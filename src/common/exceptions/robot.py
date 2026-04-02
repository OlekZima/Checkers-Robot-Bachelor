"""Robot manipulation exceptions."""

from __future__ import annotations

__all__ = [
    "DobotError",
]


class DobotError(Exception):
    """Raised when the Dobot robot arm encounters a hardware or movement error."""
