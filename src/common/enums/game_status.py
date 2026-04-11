"""Enumeration for game status."""

from __future__ import annotations

from enum import Enum

__all__ = ["GameStatus"]


class GameStatus(Enum):
    """Represents the current status of a checkers game.

    Attributes:
        IN_PROGRESS: The game is ongoing and moves are still being made.
        WON: The game has concluded with a winner.
        DRAW: The game has ended in a draw.
    """

    IN_PROGRESS = 1
    WON = 2
    DRAW = 3
