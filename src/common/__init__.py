"""Common utilities, configurations, enums, and exceptions for the checkers robot project."""

from __future__ import annotations

from src.common.configs import ColorConfig, RecognitionConfig
from src.common.enums import (
    CalibrationMethod,
    Color,
    GameReportField,
    GameStatus,
    MoveValidationResult,
)
from src.common.exceptions import (
    BoardDetectionError,
    BoardError,
    BoardMappingError,
    CameraReadError,
    CheckersError,
    CheckersGameEndError,
    CheckersGameNotPermittedMoveError,
    CV2Error,
    DecisionEngineError,
    DobotError,
    InsufficientDataError,
    NoStartTileError,
)

__all__ = [
    # Configs
    "ColorConfig",
    "RecognitionConfig",
    # Enums
    "Color",
    "GameStatus",
    "MoveValidationResult",
    "CalibrationMethod",
    "GameReportField",
    # Exceptions
    "BoardError",
    "NoStartTileError",
    "BoardDetectionError",
    "InsufficientDataError",
    "BoardMappingError",
    "CV2Error",
    "CameraReadError",
    "CheckersError",
    "CheckersGameEndError",
    "CheckersGameNotPermittedMoveError",
    "DecisionEngineError",
    "DobotError",
]
