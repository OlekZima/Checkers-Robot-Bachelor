"""Computer vision module for board and checker recognition."""

from __future__ import annotations

from src.computer_vision.board_recognition.board import Board
from src.computer_vision.board_recognition.board_detector import BoardDetector
from src.computer_vision.board_recognition.board_tile import BoardTile
from src.computer_vision.board_recognition.contour_detector import ContourDetector
from src.computer_vision.board_recognition.tile_grid import TileGrid
from src.computer_vision.checker import Checker
from src.computer_vision.checker_detector import CheckerDetector
from src.computer_vision.game_state_recognition import GameState

__all__ = [
    "Board",
    "BoardDetector",
    "BoardTile",
    "Checker",
    "CheckerDetector",
    "ContourDetector",
    "GameState",
    "TileGrid",
]
