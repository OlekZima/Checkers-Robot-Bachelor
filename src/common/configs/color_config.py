"""Typed dictionary for color configurations."""

from __future__ import annotations

from typing import TypedDict

__all__ = ["ColorConfig"]


class ColorConfig(TypedDict):
    """Typed dictionary for color configurations in BGR format.

    Attributes:
        orange: BGR color for orange checkers.
        blue: BGR color for blue checkers.
        black: BGR color for black board elements.
        white: BGR color for white board elements.
    """

    orange: tuple[int, int, int]
    blue: tuple[int, int, int]
    black: tuple[int, int, int]
    white: tuple[int, int, int]
