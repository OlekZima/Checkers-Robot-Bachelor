"""Checkers game logic and AI decision making module.

This package provides the core game logic, state management,
and AI decision engine for the checkers robot.
"""

from __future__ import annotations

from src.checkers_game.checkers_game import CheckersGame
from src.checkers_game.game_controller import GameController
from src.checkers_game.negamax import NegamaxDecisionEngine

__all__ = [
    "CheckersGame",
    "GameController",
    "NegamaxDecisionEngine",
]
