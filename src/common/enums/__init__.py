"""Enumeration types used throughout the checkers robot project.

This module defines all enumeration classes used for game state tracking,
robot communication, color representation, and calibration configuration.
"""

from __future__ import annotations

from src.common.enums.calibration_method import CalibrationMethod
from src.common.enums.color import Color
from src.common.enums.game_report_field import GameReportField
from src.common.enums.game_status import GameStatus
from src.common.enums.move_validation_result import MoveValidationResult

__all__ = [
    "Color",
    "GameStatus",
    "MoveValidationResult",
    "CalibrationMethod",
    "GameReportField",
    # Backward compatibility aliases
    "Status",
    "GameStateResult",
    "RobotGameReportItem",
    "COLOR",
    "GAME_STATUS",
    "MOVE_VALIDATION_RESULT",
]

# Backward compatibility aliases
Status = GameStatus
GameStateResult = MoveValidationResult
RobotGameReportItem = GameReportField
COLOR = Color
GAME_STATUS = GameStatus
MOVE_VALIDATION_RESULT = MoveValidationResult
