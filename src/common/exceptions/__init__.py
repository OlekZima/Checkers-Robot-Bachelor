"""Custom exception hierarchy for the checkers robot project.

This module defines all custom exceptions used throughout the application,
organized by subsystem for clarity and maintainability.
"""

from __future__ import annotations

from src.common.exceptions.board import (
    BoardDetectionError,
    BoardError,
    BoardMappingError,
    InsufficientDataError,
    NoStartTileError,
)
from src.common.exceptions.decision import DecisionEngineError
from src.common.exceptions.game import (
    CheckersError,
    CheckersGameEndError,
    CheckersGameNotPermittedMoveError,
)
from src.common.exceptions.robot import DobotError
from src.common.exceptions.vision import CV2Error, CameraReadError

__all__ = [
    # Board recognition exceptions
    "BoardError",
    "NoStartTileError",
    "BoardDetectionError",
    "InsufficientDataError",
    "BoardMappingError",
    # Computer vision exceptions
    "CV2Error",
    "CameraReadError",
    # Game logic exceptions
    "CheckersError",
    "CheckersGameEndError",
    "CheckersGameNotPermittedMoveError",
    # Decision engine exceptions
    "DecisionEngineError",
    # Robot manipulation exceptions
    "DobotError",
]
