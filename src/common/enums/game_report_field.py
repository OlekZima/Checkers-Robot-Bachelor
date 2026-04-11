"""Enumeration for game report fields."""

from __future__ import annotations

from enum import Enum

__all__ = ["GameReportField"]


class GameReportField(Enum):
    """Fields included in the game state report sent to external systems.

    This enum defines the structure of the dictionary returned by the
    game controller when reporting the current game state.

    Attributes:
        GAME_STATE: Current 8x8 board state matrix.
        POINTS: Tuple of (orange_score, blue_score).
        STATUS: Current game status (IN_PROGRESS, WON, DRAW).
        WINNER: Color of the winning player, or None.
        OPTIONS: List of possible moves for the current player.
        TURN_OF: Color of the player whose turn it is.
        ROBOT_COLOR: Color assigned to the robot player.
        ROBOT_MOVE: The move the robot plans to execute.
        IS_CROWNED: Whether the robot's move results in a king piece.
    """

    GAME_STATE = 1
    POINTS = 2
    STATUS = 3
    WINNER = 4
    OPTIONS = 5
    TURN_OF = 6
    ROBOT_COLOR = 7
    ROBOT_MOVE = 8
    IS_CROWNED = 9
