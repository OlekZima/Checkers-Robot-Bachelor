"""Board recognition exceptions."""

from __future__ import annotations

__all__ = [
    "BoardError",
    "NoStartTileError",
    "BoardDetectionError",
    "InsufficientDataError",
    "BoardMappingError",
]


class BoardError(Exception):
    """Base exception for board-related errors."""


class NoStartTileError(BoardError):
    """Raised when no tile with four neighbors is found to anchor board indexing."""


class BoardDetectionError(BoardError):
    """Raised when the board detection pipeline fails to identify a valid board."""


class InsufficientDataError(BoardError):
    """Raised when there is insufficient data to complete board processing."""


class BoardMappingError(BoardError):
    """Raised when an error occurs while mapping detected tiles to grid coordinates."""
