from enum import Enum

class ReportItem(Enum):
    GAME_STATE = 1
    POINTS = 2
    STATUS = 3
    WINNER = 4
    OPTIONS = 5
    TURN_OF = 6

class RobotGameReportItem(Enum):
    GAME_STATE = 1
    POINTS = 2
    STATUS = 3
    WINNER = 4
    OPTIONS = 5
    TURN_OF = 6
    ROBOT_COLOR = 7
    ROBOT_MOVE = 8
    IS_CROWNED = 9