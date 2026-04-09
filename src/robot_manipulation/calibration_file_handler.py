"""Handles reading and writing calibration data to files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import numpy as np

from src.checkers_game.checkers_game import Color
from src.common.utils import tile_id_to_grid_coords

from .calibration_data import CalibrationData

logger = logging.getLogger(__name__)

__all__ = ["CalibrationFileHandler"]


class CalibrationFileHandler:
    """Handles reading and writing calibration data to files."""

    def __init__(self, config_path: Path) -> None:
        """Initialize with the path to the calibration configuration directory.

        Args:
            config_path: Directory path containing calibration files.
        """
        self.config_path = config_path
        self.config_path.mkdir(parents=True, exist_ok=True)

    def load_calibration(self, filename: str) -> CalibrationData:
        """Load calibration data from a file.

        Args:
            filename: Name of the calibration file (without extension).

        Returns:
            CalibrationData object populated with file contents.

        Raises:
            ValueError: If the file does not contain enough position entries.
        """
        file_path = self.config_path / f"{filename}.txt"
        if not file_path.exists():
            raise FileNotFoundError(f"Calibration file not found: {file_path}")

        with open(file_path, "r", encoding="UTF-8") as file:
            lines = file.readlines()

        if len(lines) < 42:
            raise ValueError(
                f"Calibration file must contain at least 42 lines, found {len(lines)}."
            )

        data = CalibrationData()
        self._parse_board_positions(lines, data)
        self._parse_side_pockets(lines, data)
        self._parse_dispose_area(lines, data)
        self._parse_home_position(lines, data)

        logger.info("Loaded calibration data from %s", file_path)
        return data

    def save_calibration(self, data: CalibrationData, filename: str) -> None:
        """Save calibration data to a file.

        Args:
            data: CalibrationData object to save.
            filename: Name of the output file (without extension).
        """
        file_path = self.config_path / f"{filename}.txt"

        with open(file_path, "w", encoding="UTF-8") as file:
            # Write board positions (32 tiles)
            for tile_id in range(1, 33):
                x, y = tile_id_to_grid_coords(tile_id, Color.BLUE)
                pos = data.board_positions[x][y]
                file.write(f"{pos[0]};{pos[1]};{pos[2]}\n")

            # Write side pockets (8 positions)
            for i in range(2):
                for j in range(4):
                    pos = data.side_pockets[i][j]
                    file.write(f"{pos[0]};{pos[1]};{pos[2]}\n")

            # Write dispose area and home position
            file.write(
                f"{data.dispose_area[0]};{data.dispose_area[1]};{data.dispose_area[2]}\n"
            )
            file.write(
                f"{data.home_position[0]};{data.home_position[1]};{data.home_position[2]}"
            )

        logger.info("Saved calibration data to %s", file_path)

    @staticmethod
    def _parse_calibration_line(line: str) -> List[float]:
        """Parse a single calibration line into XYZ coordinates.

        Args:
            line: Semicolon-separated string of coordinates.

        Returns:
            List of three floats.
        """
        return [float(coord) for coord in line.strip().split(";")]

    def _parse_board_positions(self, lines: List[str], data: CalibrationData) -> None:
        """Parse board tile positions from calibration file lines.

        Args:
            lines: List of lines from the calibration file.
            data: CalibrationData object to populate.
        """
        for tile_id in range(32):
            x, y = tile_id_to_grid_coords(tile_id + 1, Color.BLUE)
            data.board_positions[x][y] = self._parse_calibration_line(lines[tile_id])

    def _parse_side_pockets(self, lines: List[str], data: CalibrationData) -> None:
        """Parse side pocket positions from calibration file lines.

        Args:
            lines: List of lines from the calibration file.
            data: CalibrationData object to populate.
        """
        for i in range(32, 36):
            data.side_pockets[0][i - 32] = self._parse_calibration_line(lines[i])
        for i in range(36, 40):
            data.side_pockets[1][i - 36] = self._parse_calibration_line(lines[i])

    def _parse_dispose_area(self, lines: List[str], data: CalibrationData) -> None:
        """Parse disposal area position from calibration file lines.

        Args:
            lines: List of lines from the calibration file.
            data: CalibrationData object to populate.
        """
        data.dispose_area = np.array(self._parse_calibration_line(lines[40]))

    def _parse_home_position(self, lines: List[str], data: CalibrationData) -> None:
        """Parse home position from calibration file lines.

        Args:
            lines: List of lines from the calibration file.
            data: CalibrationData object to populate.
        """
        data.home_position = np.array(self._parse_calibration_line(lines[41]))
