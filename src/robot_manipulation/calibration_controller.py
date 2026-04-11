"""Calibration module for the robot arm.

This module provides tools for calibrating the robot arm's position
relative to the checkerboard, side pockets, disposal area, and home position.
It supports both corner-based interpolation and manual tile-by-tile calibration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from src.checkers_game.checkers_game import Color
from src.common.utils import (
    CONFIG_PATH,
    tile_id_to_grid_coords,
    lerp,
)
from src.common.exceptions import DobotError

from .calibration_data import CalibrationData
from .dobot_arm import DobotArm
from .robot_arm import RobotArm

logger = logging.getLogger(__name__)


@dataclass
class CalibrationStep:
    """Represents a single calibration step with metadata.

    Attributes:
        index: Step index in the calibration sequence.
        description: Human-readable description of the step.
        target_array: Reference to the array where the position will be stored.
        target_indices: Indices within the target array (empty for flat arrays).
    """

    index: int
    description: str
    target_array: np.ndarray
    target_indices: List[int] = field(default_factory=list)


class CalibrationController:
    """Orchestrates the robot arm calibration process.

    This class manages both corner-based interpolation calibration and
    manual tile-by-tile calibration. It provides movement controls,
    step tracking, and configuration persistence.
    """

    _HEIGHT_OFFSET: float = 20.0
    _MOVEMENT_INCREMENT: float = 1.0
    _TOTAL_CALIBRATION_POINTS: int = 42

    def __init__(self, port: str) -> None:
        """Initialize the calibration controller.

        Args:
            port: Serial port identifier for the robot arm.
        """
        CONFIG_PATH.mkdir(parents=True, exist_ok=True)

        self._arm: RobotArm = DobotArm(port)
        self._calibration_data: Optional[CalibrationData] = None
        self._base_config: Optional[np.ndarray] = None

        # Calibration state tracking
        self._corner_step_index: int = 0
        self._tile_step_index: int = 0

        # Define calibration points for corner-based calibration
        self._corner_steps: List[CalibrationStep] = self._define_corner_steps()

        logger.info("CalibrationController initialized on port %s", port)

    @property
    def arm(self) -> RobotArm:
        """Return the robot arm instance."""
        return self._arm

    @property
    def calibration_data(self) -> Optional[CalibrationData]:
        """Return the current calibration data."""
        return self._calibration_data

    # -------------------------------------------------------------------------
    # Movement Controls
    # -------------------------------------------------------------------------

    def move_forward(self) -> None:
        """Move the arm forward (positive X) by the configured increment."""
        x, y, z = self._get_current_position()
        self._arm.move_to(x + self._MOVEMENT_INCREMENT, y, z, wait=True)

    def move_backward(self) -> None:
        """Move the arm backward (negative X) by the configured increment."""
        x, y, z = self._get_current_position()
        self._arm.move_to(x - self._MOVEMENT_INCREMENT, y, z, wait=True)

    def move_left(self) -> None:
        """Move the arm left (positive Y) by the configured increment."""
        x, y, z = self._get_current_position()
        self._arm.move_to(x, y + self._MOVEMENT_INCREMENT, z, wait=True)

    def move_right(self) -> None:
        """Move the arm right (negative Y) by the configured increment."""
        x, y, z = self._get_current_position()
        self._arm.move_to(x, y - self._MOVEMENT_INCREMENT, z, wait=True)

    def move_up(self) -> None:
        """Move the arm up (positive Z) by the configured increment."""
        x, y, z = self._get_current_position()
        self._arm.move_to(x, y, z + self._MOVEMENT_INCREMENT, wait=True)

    def move_down(self) -> None:
        """Move the arm down (negative Z) by the configured increment."""
        x, y, z = self._get_current_position()
        self._arm.move_to(x, y, z - self._MOVEMENT_INCREMENT, wait=True)

    def move_to_current_position(self) -> None:
        """Move the arm to the default position for the current calibration step."""
        if self._base_config is None:
            raise ValueError("Base configuration not loaded. Load a config first.")

        if 0 <= self._tile_step_index < self._TOTAL_CALIBRATION_POINTS:
            default_pos = self._base_config[self._tile_step_index]
            self._move_to_safe_height(default_pos[0], default_pos[1], default_pos[2])
            self._arm.move_to(default_pos[0], default_pos[1], default_pos[2], wait=True)

    # -------------------------------------------------------------------------
    # Corner Calibration Phase
    # -------------------------------------------------------------------------

    def start_corner_calibration(self) -> None:
        """Initialize the corner calibration phase."""
        self._corner_step_index = 0
        logger.info("Corner calibration started")

    def get_current_corner_step_description(self) -> Optional[str]:
        """Return the description for the current corner calibration step."""
        if self._corner_step_index < len(self._corner_steps):
            step = self._corner_steps[self._corner_step_index]
            return f"Place the robot on: {step.description}"
        return None

    def move_to_current_corner_position(self) -> None:
        """Move the arm to the default position for the current corner step."""
        if self._corner_step_index < len(self._corner_steps):
            step = self._corner_steps[self._corner_step_index]
            # Use predefined default positions for corners
            default_positions = self._get_default_corner_positions()
            idx = step.index
            pos = default_positions[idx]
            self._move_to_safe_height(pos[0], pos[1], pos[2])
            self._arm.move_to(pos[0], pos[1], pos[2], wait=True)

    def save_current_corner_position(self) -> None:
        """Save the current arm position for the active corner step."""
        if self._corner_step_index < len(self._corner_steps):
            step = self._corner_steps[self._corner_step_index]
            x, y, z = self._get_current_position()

            if step.target_indices:
                target = step.target_array
                for idx in step.target_indices[:-1]:
                    target = target[idx]
                target[step.target_indices[-1]] = [x, y, z]
            else:
                step.target_array[:] = [x, y, z]

            self._move_to_safe_height(x, y, z)
            self._corner_step_index += 1
            logger.info(
                "Saved corner position %d/%d",
                self._corner_step_index,
                len(self._corner_steps),
            )

    def is_corner_calibration_complete(self) -> bool:
        """Check if all corner calibration steps are complete."""
        return self._corner_step_index >= len(self._corner_steps)

    def finalize_corner_calibration(self) -> CalibrationData:
        """Interpolate positions and finalize corner calibration.

        Returns:
            Populated CalibrationData object.
        """
        if not self.is_corner_calibration_complete():
            raise ValueError("Corner calibration is not yet complete.")

        self._calibration_data = CalibrationData()
        self._interpolate_board_positions()
        self._interpolate_side_pockets()

        # Copy interpolated data to CalibrationData
        self._calibration_data.board_positions = self._board.copy()
        self._calibration_data.side_pockets = self._side_pockets.copy()
        self._calibration_data.dispose_area = self._dispose_area.copy()
        self._calibration_data.home_position = self._home_position.copy()

        logger.info("Corner calibration finalized with interpolation")
        return self._calibration_data

    # -------------------------------------------------------------------------
    # Tile-by-Tile Calibration Phase
    # -------------------------------------------------------------------------

    def start_tile_calibration(self, config_path: Optional[Path] = None) -> None:
        """Initialize the tile-by-tile calibration phase.

        Args:
            config_path: Optional path to a base configuration file.
        """
        self._tile_step_index = 0
        self._load_base_config(config_path)
        logger.info("Tile calibration started")

    def get_current_tile_step_description(self) -> Optional[str]:
        """Return the description for the current tile calibration step."""
        if 0 <= self._tile_step_index < 32:
            return f"Calibrate board tile {self._tile_step_index + 1}"
        if 32 <= self._tile_step_index < 36:
            return f"Calibrate left side pocket {self._tile_step_index - 31}"
        if 36 <= self._tile_step_index < 40:
            return f"Calibrate right side pocket {self._tile_step_index - 35}"
        if self._tile_step_index == 40:
            return "Calibrate disposal area"
        if self._tile_step_index == 41:
            return "Calibrate home position"
        return None

    def save_current_tile_position(self) -> None:
        """Save the current arm position for the active tile step."""
        if self._base_config is None:
            raise ValueError("Base configuration not loaded.")

        if 0 <= self._tile_step_index < self._TOTAL_CALIBRATION_POINTS:
            x, y, z = self._get_current_position()
            self._base_config[self._tile_step_index] = [x, y, z]
            self._move_to_safe_height(x, y, z)
            self._tile_step_index += 1
            logger.info(
                "Saved tile position %d/%d",
                self._tile_step_index,
                self._TOTAL_CALIBRATION_POINTS,
            )

    def is_tile_calibration_complete(self) -> bool:
        """Check if all tile calibration steps are complete."""
        return self._tile_step_index >= self._TOTAL_CALIBRATION_POINTS

    def save_tile_calibration(self, filename: str) -> Path:
        """Save the tile calibration configuration to a file.

        Args:
            filename: Output filename (without extension).

        Returns:
            Path to the saved configuration file.
        """
        if self._base_config is None:
            raise ValueError("Base configuration not loaded.")

        output_path = CONFIG_PATH / f"{filename}.txt"
        with open(output_path, "w", encoding="UTF-8") as file:
            for i in range(self._TOTAL_CALIBRATION_POINTS):
                x, y, z = self._base_config[i]
                file.write(f"{x};{y};{z}\n")

        logger.info("Tile calibration saved to %s", output_path)
        return output_path

    def load_calibration_data(self, filename: str) -> CalibrationData:
        """Load calibration data from a file.

        Args:
            filename: Configuration filename (without extension).

        Returns:
            Populated CalibrationData object.
        """
        file_path = CONFIG_PATH / f"{filename}.txt"
        if not file_path.exists():
            raise FileNotFoundError(f"Calibration file not found: {file_path}")

        with open(file_path, "r", encoding="UTF-8") as file:
            lines = file.readlines()

        if len(lines) < self._TOTAL_CALIBRATION_POINTS:
            raise ValueError(
                f"File must contain {self._TOTAL_CALIBRATION_POINTS} lines, found {len(lines)}."
            )

        self._calibration_data = CalibrationData()
        self._parse_calibration_lines(lines, self._calibration_data)
        logger.info("Loaded calibration data from %s", file_path)
        return self._calibration_data

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _define_corner_steps(self) -> List[CalibrationStep]:
        """Define the sequence of corner calibration steps."""
        self._board = np.zeros((8, 8, 3), dtype=float)
        self._side_pockets = np.zeros((2, 4, 3), dtype=float)
        self._dispose_area = np.zeros(3, dtype=float)
        self._home_position = np.zeros(3, dtype=float)

        return [
            CalibrationStep(0, "upper left board corner", self._board, [0, 0]),
            CalibrationStep(1, "upper right board corner", self._board, [7, 0]),
            CalibrationStep(2, "bottom left board corner", self._board, [0, 7]),
            CalibrationStep(3, "bottom right board corner", self._board, [7, 7]),
            CalibrationStep(4, "upper left side pocket", self._side_pockets, [0, 0]),
            CalibrationStep(5, "bottom left side pocket", self._side_pockets, [0, 3]),
            CalibrationStep(6, "upper right side pocket", self._side_pockets, [1, 0]),
            CalibrationStep(7, "bottom right side pocket", self._side_pockets, [1, 3]),
            CalibrationStep(8, "disposal area", self._dispose_area),
            CalibrationStep(9, "home position", self._home_position),
        ]

    @staticmethod
    def _get_default_corner_positions() -> List[List[float]]:
        """Return default positions for corner calibration."""
        return [
            [63, 66, -2.1],  # upper left board corner
            [-41, 84, -3.8],  # upper right board corner
            [105, 229, -7],  # bottom left board corner
            [-35, 251, -6.8],  # bottom right board corner
            [93, 67.9, -6],  # upper left side pocket
            [140, 227, -10],  # bottom left side pocket
            [140, 226, -7.8],  # upper right side pocket
            [-68, 89, -8],  # bottom right side pocket
            [130, -150, 3],  # disposal area
            [90, -140, 0],  # home position
        ]

    def _load_base_config(self, config_path: Optional[Path] = None) -> None:
        """Load or initialize the base configuration array.

        Args:
            config_path: Optional path to a configuration file.
        """
        if config_path and config_path.exists():
            with open(config_path, "r", encoding="UTF-8") as file:
                lines = file.readlines()
            if len(lines) < self._TOTAL_CALIBRATION_POINTS:
                raise ValueError("Configuration file has insufficient lines.")
            self._base_config = np.array(
                [
                    [float(v) for v in line.strip().split(";")]
                    for line in lines[: self._TOTAL_CALIBRATION_POINTS]
                ]
            )
        else:
            # Initialize with current position as fallback
            x, y, z = self._get_current_position()
            self._base_config = np.full(
                (self._TOTAL_CALIBRATION_POINTS, 3), [x, y, z], dtype=float
            )

    def _get_current_position(self) -> Tuple[float, float, float]:
        """Get the current XYZ position of the robot arm.

        Returns:
            Tuple of (x, y, z) coordinates.

        Raises:
            DobotError: If the arm is not connected.
        """
        x, y, z, _ = self._arm.get_pose()
        return x, y, z

    def _move_to_safe_height(self, x: float, y: float, z: float) -> None:
        """Move the arm to a position with a safety Z offset.

        Args:
            x: X coordinate.
            y: Y coordinate.
            z: Base Z coordinate.
        """
        self._arm.move_to(x, y, z + self._HEIGHT_OFFSET, wait=True)

    @staticmethod
    def _parse_calibration_lines(lines: List[str], data: CalibrationData) -> None:
        """Parse calibration file lines into CalibrationData.

        Args:
            lines: List of semicolon-separated coordinate strings.
            data: CalibrationData object to populate.
        """
        # Parse board positions (32 tiles)
        for tile_id in range(1, 33):
            x, y = tile_id_to_grid_coords(tile_id, Color.BLUE)
            coords = [float(v) for v in lines[tile_id - 1].strip().split(";")]
            data.board_positions[x][y] = coords

        # Parse side pockets (8 positions)
        for i in range(32, 36):
            coords = [float(v) for v in lines[i].strip().split(";")]
            data.side_pockets[0][i - 32] = coords
        for i in range(36, 40):
            coords = [float(v) for v in lines[i].strip().split(";")]
            data.side_pockets[1][i - 36] = coords

        # Parse disposal area and home position
        data.dispose_area = np.array([float(v) for v in lines[40].strip().split(";")])
        data.home_position = np.array([float(v) for v in lines[41].strip().split(";")])

    def _interpolate_board_positions(self) -> None:
        """Interpolate board tile positions from the 4 calibrated corners."""
        # Interpolate border tiles
        for i in range(1, 7):
            t = i / 7.0
            for k in range(3):
                self._board[0][i][k] = lerp(
                    self._board[0][0][k], self._board[0][7][k], t
                )
                self._board[7][i][k] = lerp(
                    self._board[7][0][k], self._board[7][7][k], t
                )
                self._board[i][0][k] = lerp(
                    self._board[0][0][k], self._board[7][0][k], t
                )
                self._board[i][7][k] = lerp(
                    self._board[0][7][k], self._board[7][7][k], t
                )

        # Interpolate inner tiles
        for x in range(1, 7):
            t_x = x / 7.0
            for y in range(1, 7):
                t_y = y / 7.0
                for z in range(3):
                    yz_interp = lerp(self._board[0][y][z], self._board[7][y][z], t_x)
                    xz_interp = lerp(self._board[x][0][z], self._board[x][7][z], t_y)
                    self._board[x][y][z] = (yz_interp + xz_interp) / 2.0

    def _interpolate_side_pockets(self) -> None:
        """Interpolate side pocket positions from the endpoints."""
        for k in range(3):
            self._side_pockets[0][1][k] = (
                self._side_pockets[0][0][k] * 2 + self._side_pockets[0][3][k]
            ) / 3.0
            self._side_pockets[1][1][k] = (
                self._side_pockets[1][0][k] * 2 + self._side_pockets[1][3][k]
            ) / 3.0
            self._side_pockets[0][2][k] = (
                self._side_pockets[0][0][k] + self._side_pockets[0][3][k] * 2
            ) / 3.0
            self._side_pockets[1][2][k] = (
                self._side_pockets[1][0][k] + self._side_pockets[1][3][k] * 2
            ) / 3.0
