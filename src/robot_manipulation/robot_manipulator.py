"""Facade for robot manipulation operations."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from src.checkers_game.checkers_game import Color
from src.common.exceptions import DobotError

from .calibration_data import CalibrationData
from .calibration_file_handler import CalibrationFileHandler
from .dobot_arm import DobotArm
from .king_manager import KingManager
from .move_executor import MoveExecutor

logger = logging.getLogger(__name__)

__all__ = ["RobotManipulator"]


class RobotManipulator:
    """Facade for robot manipulation operations.

    This class provides a high-level interface for controlling the robot arm,
    coordinating calibration, move execution, and king piece management.
    """

    def __init__(
        self,
        port: str,
        config_path: Path,
        robot_color: Color,
        config_filename: str = "calibration",
        height_offset: float = 10.0,
        retry_limit: int = 5,
    ) -> None:
        """Initialize the robot manipulator.

        Args:
            port: Serial port for the Dobot device.
            config_path: Directory containing calibration files.
            robot_color: The color this robot is playing as.
            config_filename: Name of the calibration file to load.
            height_offset: Safety height above the board for movements.
            retry_limit: Maximum number of retries for failed movements.
        """
        self._arm = DobotArm(port)
        self._calibration_handler = CalibrationFileHandler(config_path)
        self._calibration = self._calibration_handler.load_calibration(config_filename)
        self._robot_color = robot_color
        self._height_offset = height_offset
        self._retry_limit = retry_limit

        self._move_executor = MoveExecutor(
            self._arm, self._calibration, robot_color, height_offset
        )
        self._king_manager = KingManager(self._arm, self._calibration, height_offset)

        logger.info("RobotManipulator initialized on port %s", port)

    def execute_move(self, move_sequence: List[int], is_crown: bool = False) -> None:
        """Execute a complete move, optionally crowning the piece.

        Args:
            move_sequence: List of tile IDs representing the move path.
            is_crown: Whether to place a king crown at the destination.
        """
        try:
            self._move_executor.execute_move(move_sequence)

            if is_crown:
                destination_tile = move_sequence[-1]
                self._king_manager.place_crown(destination_tile)

            self._move_executor.go_home()
        except Exception as exc:
            logger.error("Failed to execute move: %s", exc)
            self._attempt_recovery(move_sequence)
            raise DobotError(f"Failed to execute move: {exc}") from exc

    def go_home(self) -> None:
        """Move the arm to the home position."""
        self._move_executor.go_home()

    def initialize(self) -> None:
        """Initialize the robot arm and move to home position."""
        home = self._calibration.home_position
        self._move_to_safe_position(home[0], home[1], home[2])
        self._arm.move_to(home[0], home[1], home[2], wait=True)
        logger.info("Robot arm initialized and moved to home position")

    @property
    def kings_remaining(self) -> int:
        """Return the number of available king pieces."""
        return self._king_manager.kings_remaining

    def _move_to_safe_position(self, x: float, y: float, z: float) -> None:
        """Move to a position with a safety offset in Z.

        Args:
            x: X coordinate.
            y: Y coordinate.
            z: Base Z coordinate.
        """
        self._arm.move_to(x, y, z + self._height_offset, wait=True)

    def _attempt_recovery(self, move_sequence: List[int]) -> None:
        """Attempt to recover from a failed movement.

        Args:
            move_sequence: The move sequence that failed.
        """
        logger.warning("Attempting recovery after failed move")
        try:
            current_pose = self._arm.get_pose()
            self._arm.move_to(
                current_pose[0] + 1, current_pose[1] + 1, current_pose[2] + 1, wait=True
            )
            self._move_executor.go_home()
        except Exception as recovery_exc:
            logger.error("Recovery failed: %s", recovery_exc)
