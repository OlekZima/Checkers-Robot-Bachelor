"""Enumeration for checker piece colors."""

from __future__ import annotations

from enum import IntEnum

__all__ = ["Color"]


class Color(IntEnum):
    """Represents the color of a checker piece.

    Positive values indicate ORANGE pieces, negative values indicate BLUE pieces.
    This convention allows easy multiplication checks for piece ownership.

    Attributes:
        ORANGE: Orange checker pieces (value: 1).
        BLUE: Blue checker pieces (value: -1).
    """

    ORANGE = 1
    BLUE = -1
