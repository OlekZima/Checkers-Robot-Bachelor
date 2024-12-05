from typing import Optional, List
from pathlib import Path
import numpy as np

from pydobotplus import Dobot
from src.checkers_game_and_decisions.checkers_game import Color
from src.common.utilities import get_coord_from_tile_id
from src.common.exceptions import DobotError


class BaseRobotController:
    """Base class for robot control with common functionalities"""

    _HEIGHT_OFFSET: float = 10.0
    _CONFIG_PATH: Path = Path("configs")

    def __init__(self, device: Dobot, color: Color, config_path: Optional[str] = None):
        self._CONFIG_PATH.mkdir(exist_ok=True)
        self.color = color
        self.device = device

        self._board = np.zeros((8, 8, 3), dtype=float)
        self._side_pockets = np.zeros((2, 4, 3), dtype=float)
        self._dispose_area = np.zeros(3, dtype=float)
        self._home_pos = np.zeros(3, dtype=float)
        self._base_config = None

        if config_path:
            self.read_calibration_file(config_path)

    def read_calibration_file(self, file_path: str):
        """Read calibration configuration from file"""
        try:
            with open(file_path, "r", encoding="UTF-8") as f:
                lines = f.readlines()
                if len(lines) < 42:
                    raise ValueError("Configuration file must contain 42 lines")
                self._parse_config_lines(lines)
        except IOError as e:
            print(f"Error reading calibration file: {e}")

    def _parse_config_lines(self, lines: List[str]):
        """Parse configuration lines and populate internal arrays"""
        self._base_config = [
            [float(coord) for coord in line.strip().split(";")] for line in lines[:42]
        ]

        # Board positions
        for i in range(0, 32):
            x, y = get_coord_from_tile_id(i + 1, self.color)
            self._board[x][y] = self._base_config[i]

        # Side pockets
        for i in range(32, 36):
            self._side_pockets[0][i - 32] = self._base_config[i]
        for i in range(36, 40):
            self._side_pockets[1][i - 36] = self._base_config[i]

        # Dispose and home positions
        self._dispose_area = self._base_config[40]
        self._home_pos = self._base_config[41]

    def _move_arm_safely(self, x: float, y: float, z: float, wait: bool = True):
        """Safe arm movement with error handling"""
        try:
            self.device.clear_alarms()
            self.device.move_to(x, y, z, wait=wait)
        except DobotError as exc:
            print(f"Movement error: {exc}")

    def _get_position(self) -> tuple[float, float, float]:
        x, y, z, _ = self.device.get_pose().position
        return x, y, z

    def move_to_home(self):
        """Move robot to home position"""
        self._move_arm_safely(self._home_pos[0], self._home_pos[1], self._home_pos[2])
