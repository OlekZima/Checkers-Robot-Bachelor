"""Board recognition subpackage for detecting checkerboards and tiles."""

from __future__ import annotations

from src.computer_vision.board_recognition.board import Board
from src.computer_vision.board_recognition.board_detector import BoardDetector
from src.computer_vision.board_recognition.board_tile import BoardTile
from src.computer_vision.board_recognition.contour_detector import ContourDetector
from src.computer_vision.board_recognition.tile_grid import TileGrid

__all__ = [
    "Board",
    "BoardDetector",
    "BoardTile",
    "ContourDetector",
    "TileGrid",
]
