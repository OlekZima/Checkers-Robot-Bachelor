"""Dataclass representing a detected checker piece."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from src.common.enums import Color


@dataclass
class Checker:
    """Represents a detected checker piece on the board.

    Attributes:
        color: The color of the checker piece (ORANGE or BLUE).
        position: The (x, y) grid coordinates of the checker on the board.
    """

    color: Color
    position: Tuple[int, int]

    def __repr__(self) -> str:
        return f"Checker(color={self.color.name}, position={self.position})"
