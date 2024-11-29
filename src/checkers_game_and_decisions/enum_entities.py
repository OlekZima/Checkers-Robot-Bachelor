"""Module storing enums for the project."""

from enum import Enum


class RobotGameReportItem(Enum):
    """Enum for Game event report items."""

    GAME_STATE = 1
    POINTS = 2
    STATUS = 3
    WINNER = 4
    OPTIONS = 5
    TURN_OF = 6
    ROBOT_COLOR = 7
    ROBOT_MOVE = 8
    IS_CROWNED = 9


class Color(Enum):
    """Enum representing the color of the player and robot."""

    ORANGE = 1
    BLUE = -1


class Status(Enum):
    """Enum representing the status of the whole game."""

    IN_PROGRESS = 1
    WON = 2
    DRAW = 3


class GameStateResult(Enum):
    """Enum representing the current state of the move."""

    INVALID_ROBOT_MOVE = 1
    VALID_WRONG_ROBOT_MOVE = 2
    VALID_RIGHT_ROBOT_MOVE = 3
    NO_ROBOT_MOVE = 4
    INVALID_OPPONENT_MOVE = 5
    VALID_OPPONENT_MOVE = 6
    NO_OPPONENT_MOVE = 7
