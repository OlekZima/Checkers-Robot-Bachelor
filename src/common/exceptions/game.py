"""Game logic exceptions."""

from __future__ import annotations

__all__ = [
    "CheckersError",
    "CheckersGameEndError",
    "CheckersGameNotPermittedMoveError",
]


class CheckersError(Exception):
    """Base exception for checkers game logic errors."""


class CheckersGameEndError(CheckersError):
    """Raised when attempting to calculate a move after the game has ended."""


class CheckersGameNotPermittedMoveError(CheckersError):
    """Raised when a player attempts an illegal or unpermitted move."""
