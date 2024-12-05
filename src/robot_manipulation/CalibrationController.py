import os
from pathlib import Path
from typing import Optional

import numpy as np
from pydobotplus import Dobot

from src.common.utilities import (
    # flush_input,
    get_coord_from_tile_id,
    linear_interpolate,
)
from src.common.exceptions import DobotError


class CalibrationController:
    """Configuration controller for the DOBOT arm."""

    _HEIGHT_OFFSET: float = 10.0
    _INCREMENT: float = 1.0
    _CONFIG_PATH: Path = Path("configs")

    def __init__(self, dobot_port) -> None:
        self._CONFIG_PATH.mkdir(exist_ok=True)

        self.base_config = None

        # Connecting to DOBOT
        self.device = Dobot(dobot_port)

        # Corner calibration
        # Board field numerating convention:
        #  upper_left = [0][0]
        #  upper_right = [7][0]
        #  bottom_left = [0][7]
        #  bottom_right = [7][7]
        self._board = np.zeros((8, 8, 3), dtype=float)
        self._side_pockets = np.zeros((2, 4, 3), dtype=float)
        self._dispose_area = np.zeros(3, dtype=float)
        self._home_pos = np.zeros(3, dtype=float)

        self._default_calibration_positions = [
            [244, 73, -9],  # upper left board corner
            [246, -71, -11],  # upper right board corner
            [77, 54, -4],  # bottom left board corner
            [77, -53, -4],  # bottom right board corner
            [246, 106.5, -8.9],  # upper left side pocket
            [84, 87, -5],  # bottom left side pocket
            [246, -104, -9.2],  # upper right side pocket
            [84, -85, -5],  # bottom right side pocket
            [130, -150, 3],  # disposal area
            [90, -140, 0],  # home position
        ]

        self.calibration_points = self._prepare_calibration_points()
        self._current_corner_calibration_index = 0
        self._current_all_tiles_calibration_index = 0

    def get_board_pos(self):
        return self._board

    def get_side_pockets_pos(self):
        return self._side_pockets

    def get_home_pos(self):
        return self._home_pos

    def get_dispose_pos(self):
        return self._dispose_area

    @staticmethod
    def get_config_path() -> Path:
        return CalibrationController._CONFIG_PATH

    def move_forward(self) -> None:
        """Move the arm forward from robots perspective by a specified increment."""
        x, y, z = self._get_xyz_position()
        x += self._INCREMENT
        self._move_arm(x, y, z, wait=True)

    def move_backward(self) -> None:
        """Move the arm backward from robots perspective by a specified increment."""
        x, y, z = self._get_xyz_position()
        x -= self._INCREMENT
        self._move_arm(x, y, z, wait=True)

    def move_left(self) -> None:
        """Move the arm left from robots perspective by a specified increment."""
        x, y, z = self._get_xyz_position()
        y += self._INCREMENT
        self._move_arm(x, y, z, wait=True)

    def move_right(self) -> None:
        """Move the arm right from robots perspective by a specified increment."""
        x, y, z = self._get_xyz_position()
        y -= self._INCREMENT
        self._move_arm(x, y, z, wait=True)

    def move_up(self):
        """Move the arm up from robots perspective by a specified increment."""
        x, y, z = self._get_xyz_position()
        z += self._INCREMENT
        self._move_arm(x, y, z, wait=True)

    def move_down(self):
        """Move the arm down from robots perspective by a specified increment."""
        x, y, z = self._get_xyz_position()
        z -= self._INCREMENT
        self._move_arm(x, y, z, wait=True)

    def _get_xyz_position(self) -> tuple[float, float, float]:
        x, y, z, _ = self.device.get_pose().position
        return x, y, z

    def move_to_current_all_tiles_calibration_position(self):
        """Move the robot to the default position for the current all tiles calibration point."""
        if 0 <= self._current_all_tiles_calibration_index < 42:
            default_pos = self.base_config[self._current_all_tiles_calibration_index]
            self._move_arm(
                default_pos[0],
                default_pos[1],
                default_pos[2] + self._HEIGHT_OFFSET,
                wait=True,
            )
            self._move_arm(default_pos[0], default_pos[1], default_pos[2], wait=True)
        else:
            pass

    def get_current_all_tiles_calibration_step(self):
        """Retrieve the instruction for the current all tiles calibration point."""
        if 0 <= self._current_all_tiles_calibration_index < 32:
            return (
                f"Calibrate board tile {self._current_all_tiles_calibration_index + 1}"
            )
        if 32 <= self._current_all_tiles_calibration_index < 36:
            return f"Calibrate left side pocket {self._current_all_tiles_calibration_index - 31}"
        if 36 <= self._current_all_tiles_calibration_index < 40:
            return f"Calibrate right side pocket {self._current_all_tiles_calibration_index - 35}"
        if self._current_all_tiles_calibration_index == 40:
            return "Calibrate dispose area"
        if self._current_all_tiles_calibration_index == 41:
            return "Calibrate home position"
        else:
            return None

    def save_current_all_tiles_calibration_position(self):
        """Save the adjusted position for the current all tiles calibration point."""
        if 0 <= self._current_all_tiles_calibration_index < 42:
            x, y, z = self._get_xyz_position()

            self.base_config[self._current_all_tiles_calibration_index] = [x, y, z]

            self._move_arm(x, y, z + self._HEIGHT_OFFSET, wait=True)

            self._current_all_tiles_calibration_index += 1
        else:
            pass

    def is_all_tiles_calibration_complete(self):
        """Check if the all tiles calibration process is complete."""
        return self._current_all_tiles_calibration_index >= 42

    def save_all_tiles_config(self, filename: str):
        """Save the all tiles calibration configuration."""
        config_path = self._CONFIG_PATH / f"{filename}.txt"

        with open(config_path, mode="w", encoding="UTF-8") as config_file:
            for i in range(0, 42):
                base_x, base_y, base_z = self.base_config[i]
                config_file.write(f"{base_x};{base_y};{base_z}\n")

    def _prepare_calibration_points(self):
        """Prepare the list of calibration points for step-by-step calibration."""
        calibration_points = [
            # List of tuples containing index, storage_array, storage_indices, description
            (0, self._board, [0, 0], "upper left board corner"),
            (1, self._board, [7, 0], "upper right board corner"),
            (2, self._board, [0, 7], "bottom left board corner"),
            (3, self._board, [7, 7], "bottom right board corner"),
            (4, self._side_pockets, [0, 0], "upper left side pocket"),
            (5, self._side_pockets, [0, 3], "bottom left side pocket"),
            (6, self._side_pockets, [1, 0], "upper right side pocket"),
            (7, self._side_pockets, [1, 3], "bottom right side pocket"),
            (8, self._dispose_area, [], "dispose area"),
            (9, self._home_pos, [], "default/home position"),
        ]

        return calibration_points

    def start_corner_calibration(self):
        """Initialize the calibration process."""
        self._current_corner_calibration_index = 0

    def get_current_corner_calibration_step(self):
        """Retrieve the instruction for the current calibration point."""
        if self._current_corner_calibration_index < len(self.calibration_points):
            _, _, _, description = self.calibration_points[
                self._current_corner_calibration_index
            ]
            return f"Please place the DOBOT on {description} (from its perspective)"
        return None

    def move_to_current_corner_calibration_position(self):
        """Move the robot to the default position for the current calibration point."""
        if self._current_corner_calibration_index < len(self.calibration_points):
            idx, _, _, _ = self.calibration_points[
                self._current_corner_calibration_index
            ]
            default_pos = self._default_calibration_positions[idx]
            self._move_arm(
                default_pos[0],
                default_pos[1],
                default_pos[2] + self._HEIGHT_OFFSET,
                wait=True,
            )
            self._move_arm(default_pos[0], default_pos[1], default_pos[2], wait=True)
        else:
            pass

    def save_current_corner_calibration_position(self):
        """Save the adjusted position for the current calibration point."""
        if self._current_corner_calibration_index < len(self.calibration_points):
            _, storage_array, storage_indices, _ = self.calibration_points[
                self._current_corner_calibration_index
            ]
            x, y, z = self._get_xyz_position()

            piece_storage = storage_array
            if storage_indices:
                for i in storage_indices[:-1]:
                    piece_storage = piece_storage[i]
                storage_idx = storage_indices[-1]
                piece_storage[storage_idx][:] = [x, y, z]
            else:
                piece_storage[:] = [x, y, z]

            self._move_arm(x, y, z + self._HEIGHT_OFFSET, wait=True)

            self._current_corner_calibration_index += 1
        else:
            pass

    def is_corner_calibration_complete(self):
        """Check if the calibration process is complete."""
        return self._current_corner_calibration_index >= len(self.calibration_points)

    def finalize_corner_calibration(self):
        """Perform final steps after calibration (e.g., interpolation)."""
        self._interpolate_board_tiles()
        self._interpolate_side_pockets()

    # endregion

    def _move_arm(self, x, y, z, wait: Optional[bool] = True) -> None:
        try:
            self.device.clear_alarms()
            self.device.move_to(x, y, z, wait=wait)
        except DobotError as exc:
            print(exc)

    def _interpolate_board_tiles(self) -> None:
        # 1) Interpolating border tiles coordinates
        for i in range(1, 7):
            t = i / 7.0
            for k in range(3):
                # 1.1) Left column (x = 0)
                self._board[0][i][k] = linear_interpolate(
                    self._board[0][0][k], self._board[0][7][k], t
                )
                # 1.2) Right column (x = 7)
                self._board[7][i][k] = linear_interpolate(
                    self._board[7][0][k], self._board[7][7][k], t
                )
                # 1.3 Upper row (y = 0)
                self._board[i][0][k] = linear_interpolate(
                    self._board[0][0][k], self._board[7][0][k], t
                )
                # Bottom row (y = 7)
                self._board[i][7][k] = linear_interpolate(
                    self._board[0][7][k], self._board[7][7][k], t
                )

        # 2) Interpolating inner points
        for x in range(1, 7):
            t_x = x / 7.0
            for y in range(1, 7):
                t_y = y / 7.0
                for z in range(3):
                    yz_interpolation = linear_interpolate(
                        self._board[0][y][z], self._board[7][y][z], t_x
                    )
                    xz_interpolation = linear_interpolate(
                        self._board[x][0][z], self._board[x][7][z], t_y
                    )
                    self._board[x][y][z] = (yz_interpolation + xz_interpolation) / 2.0

    def _interpolate_side_pockets(self) -> None:
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

    def read_file_config(self, path: str) -> None:
        configs = os.listdir(self._CONFIG_PATH)

        if len(configs) == 0:
            print("No configuration files found.")
            print("Calibration should be done from scratch.")
            x, y, z, _ = self.device.get_pose().position
            config: list[list[int]] = [[x, y, z] for _ in range(42)]
            self.base_config = config
            return

        base_config_path = self._CONFIG_PATH / path
        config: np.ndarray = np.zeros((42, 3), dtype=float)
        with open(base_config_path, "r", encoding="UTF-8") as config_file:
            file_lines = config_file.readlines()
            if len(file_lines) < 42:
                raise ValueError(
                    """Configuration file must contain 42 lines.
                    Please select a correct configuration file."""
                )

            for i in range(0, 42):
                positions: list[str] = file_lines[i].split(";")
                config[i] = positions

            self.base_config = config

    def save_corners_config(self, file_name: str) -> None:
        """Save the interpolated calibration points for the corners to a file."""
        config_path = self._CONFIG_PATH / f"{file_name}.txt"
        config_path.touch(exist_ok=True)

        with open(config_path, mode="w", encoding="UTF-8") as f:
            for i in range(1, 33):
                x, y = get_coord_from_tile_id(i)
                f.write(
                    f"{self._board[x][y][0]};{self._board[x][y][1]};{self._board[x][y][2]}\n"
                )

            for i in range(2):
                for j in range(4):
                    f.write(
                        f"{self._side_pockets[i][j][0]};{self._side_pockets[i][j][1]};{self._side_pockets[i][j][2]}\n"
                    )

            f.write(
                f"{self._dispose_area[0]};{self._dispose_area[1]};{self._dispose_area[2]}\n"
            )

            f.write(f"{self._home_pos[0]};{self._home_pos[1]};{self._home_pos[2]}")
