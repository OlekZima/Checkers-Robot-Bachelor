from enum import IntEnum


class RobotGameReportItem(IntEnum):
    GAME_STATE = 1
    POINTS = 2
    STATUS = 3
    WINNER = 4
    OPTIONS = 5
    TURN_OF = 6
    ROBOT_COLOR = 7
    ROBOT_MOVE = 8
    IS_CROWNED = 9


class Color(IntEnum):
    ORANGE = 1
    BLUE = -1


class Status(IntEnum):
    IN_PROGRESS = 1
    WON = 2
    DRAW = 3


class UpdateGameStateResult(IntEnum):
    INVALID_ROBOT_MOVE = 1
    VALID_WRONG_ROBOT_MOVE = 2
    VALID_RIGHT_ROBOT_MOVE = 3
    NO_ROBOT_MOVE = 4
    INVALID_OPPONENT_MOVE = 5
    VALID_OPPONENT_MOVE = 6
    NO_OPPONENT_MOVE = 7
