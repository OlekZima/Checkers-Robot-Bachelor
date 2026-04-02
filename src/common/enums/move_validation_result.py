"""Enumeration for move validation results."""

from __future__ import annotations

from enum import Enum

__all__ = ["MoveValidationResult"]


class MoveValidationResult(Enum):
    """Represents the result of validating a detected move against the game state.

    This enum is used by the game controller to determine how to respond
    to changes detected by the computer vision system.

    Attributes:
        INVALID_ROBOT_MOVE: The robot attempted an illegal move.
        VALID_WRONG_ROBOT_MOVE: The robot made a legal move, but not the one it planned.
        VALID_RIGHT_ROBOT_MOVE: The robot executed its planned move correctly.
        NO_ROBOT_MOVE: No move was detected during the robot's turn.
        INVALID_OPPONENT_MOVE: The opponent attempted an illegal move.
        VALID_OPPONENT_MOVE: The opponent made a legal move.
        NO_OPPONENT_MOVE: No move was detected during the opponent's turn.
    """

    INVALID_ROBOT_MOVE = 1
    VALID_WRONG_ROBOT_MOVE = 2
    VALID_RIGHT_ROBOT_MOVE = 3
    NO_ROBOT_MOVE = 4
    INVALID_OPPONENT_MOVE = 5
    VALID_OPPONENT_MOVE = 6
    NO_OPPONENT_MOVE = 7
