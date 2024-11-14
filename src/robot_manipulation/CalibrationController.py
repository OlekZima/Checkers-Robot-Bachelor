import os
from os.path import exists
from typing import Optional

from serial.tools import list_ports
from pydobotplus import Dobot
import numpy as np
import cv2

from src.checkers_game_and_decissions.utilities import linear_interpolate, get_coord_from_field_id, flush_input


class CalibrationController:

    def __init__(self, external_device: Optional[Dobot] = None) -> None:
        # Connecting to DOBOT
        self.base_config = None

        if external_device is None:
            available_ports = list_ports.comports()
            self.device = self.connect_to_dobot(available_ports)
        else:
            self.device = external_device

        self.configs_path = "src/robot_manipulation/configuration_files"
        os.makedirs(self.configs_path, exist_ok=True)

        self.offset_height: float = 10.0

    @staticmethod
    def connect_to_dobot(available_ports: list) -> Dobot:
        print("\nPlease select port by index")
        for i, p in enumerate(available_ports):
            print(f"[{i}]: {p}")

        port_idx = int(input())
        port = available_ports[port_idx].device
        return Dobot(port=port)

    def calibrate(self) -> None:
        input_method = None
        print("Select calibration method (all/corners):")
        while input_method not in ["all", "corners"]:
            input_method = input().strip().lower()

        self._calibrate(input_method)
        print("\nCalibration done\n")

    def _calibrate(self, method: str) -> None:
        if method == "all":
            self._read_file_config()
            self._calibrate_all_fields()
            self._save_all_field_config()
        else:
            self._calibrate_corners()
            self._save_corners_config()

    def _move_and_update(self, index: int, offset_height: float) -> None:
        """Move arm to a specified position and update base_config at the given index."""
        if self.base_config is not None:
            self._move_arm(
                self.base_config[index][0],
                self.base_config[index][1],
                self.base_config[index][2] + offset_height,
                True,
            )
        self._move_arm(
            self.base_config[index][0],
            self.base_config[index][1],
            self.base_config[index][2],
            True,
        )
        print(f"\nSet to position of id {index + 1}")
        self._keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.base_config[index][0] = x
        self.base_config[index][1] = y
        self.base_config[index][2] = z
        self._move_arm(x, y, z + offset_height, True)

    def _calibrate_all_fields(self) -> None:
        # Calibrate fields in 3 ranges: 0-31, 32-35, 36-39, and special positions 40 and 41.

        # Calibrate positions 0 to 31
        for i in range(32):
            self._move_and_update(i, self.offset_height)

        # Calibrate positions 32 to 35 (side pocket left)
        for i in range(32, 36):
            print(f"\nSet to side pocket (left) of id {i - 31}")
            self._move_and_update(i, self.offset_height)

        # Calibrate positions 36 to 39 (side pocket right)
        for i in range(36, 40):
            print(f"\nSet to side pocket (right) of id {i - 35}")
            self._move_and_update(i, self.offset_height)

        # Calibrate position 40 (dispose area)
        print("\nSet to dispose area")
        self._move_and_update(40, self.offset_height)

        # Calibrate position 41 (home position)
        print("\nSet to home position")
        self._move_and_update(41, self.offset_height)

    def _calibrate_corners(self) -> None:
        # Corner calibration
        # Board field numerating convention:
        #  upper_left = [0][0]
        #  upper_right = [7][0]
        #  bottom_left = [0][7]
        #  bottom_right = [7][7]
        self.board = np.zeros((8, 8, 3), dtype=float)
        self.side_pockets = np.zeros((2, 4, 3), dtype=float)
        self.dispose_area = np.zeros(3, dtype=float)
        self.home_pos = np.zeros(3, dtype=float)

        self.default_calibration_positions = [
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

        def _calibrate_point(
                index: int, storage_array: np.ndarray, storage_indices: list, message_info: str
        ):
            print(message_info)
            default_pos = self.default_calibration_positions[index]
            # Move to default position plus height
            self._move_arm(
                default_pos[0],
                default_pos[1],
                default_pos[2] + self.offset_height,
                wait=True,
            )
            self._move_arm(default_pos[0], default_pos[1], default_pos[2], wait=True)
            self._keyboard_move_dobot()
            x, y, z, _ = self.device.get_pose().position

            piece_storage = storage_array
            if storage_indices:
                for i in storage_indices[:-1]:
                    piece_storage = piece_storage[i]
                storage_idx = storage_indices[-1]
                piece_storage[storage_idx][:] = [x, y, z]
            else:
                piece_storage[:] = [x, y, z]
            print(f"x = {x}\ty = {y}\tz = {z}")
            # Move the arm back up
            self._move_arm(x, y, z + +self.offset_height, wait=True)

        calibration_points = [
            (0, self.board, [0, 0], "upper left board corner"),
            (1, self.board, [7, 0], "upper right board corner"),
            (2, self.board, [0, 7], "bottom left board corner"),
            (3, self.board, [7, 7], "bottom right board corner"),
            (4, self.side_pockets, [0, 0], "upper left side pocket"),
            (5, self.side_pockets, [0, 3], "bottom left side pocket"),
            (6, self.side_pockets, [1, 0], "upper right side pocket"),
            (7, self.side_pockets, [1, 3], "bottom right side pocket"),
            (8, self.dispose_area, [], "dispose area"),
            (9, self.home_pos, [], "default/home position"),
        ]

        for idx, storage, indices, description in calibration_points:
            message = f"Please place the DOBOT on {description} (from its perspective)"
            _calibrate_point(idx, storage, indices, message)

        self._interpolate_board_fields()
        self._interpolate_side_pockets()

    def _keyboard_move_dobot(self, increment: float = 1.0) -> None:
        x, y, z, _ = self.device.get_pose().position

        instruction_frame = np.zeros(
            shape=(300, 300)
        )  # TODO - instruction how to use frame

        while True:
            self._move_arm(x, y, z, wait=True)
            cv2.imshow("Calibrate instruction", instruction_frame)
            key = cv2.waitKey(0)

            x, y, z, _ = self.device.get_pose().position

            if key == 13:
                break
            elif key == ord("w"):
                x += increment
            elif key == ord("s"):
                x -= increment
            elif key == ord("a"):
                y += increment
            elif key == ord("d"):
                y -= increment
            elif key == ord("q"):
                z -= increment
            elif key == ord("e"):
                z += increment
            elif key == 27:
                cv2.destroyAllWindows()
                exit(1)

        cv2.destroyAllWindows()

    def _move_arm(self, x, y, z, wait: Optional[bool] = True) -> None:
        try:
            self.device.clear_alarms()
            self.device.move_to(x, y, z, wait=wait)
        except Exception as e:
            print(e)

    def _interpolate_board_fields(self) -> None:
        # 1) Interpolating border fields coordinates
        for i in range(1, 7):
            t = i / 7.0
            for k in range(3):
                # 1.1) Left column (x = 0)
                self.board[0][i][k] = linear_interpolate(
                    self.board[0][0][k], self.board[0][7][k], t
                )
                # 1.2) Right column (x = 7)
                self.board[7][i][k] = linear_interpolate(
                    self.board[7][0][k], self.board[7][7][k], t
                )
                # 1.3 Upper row (y = 0)
                self.board[i][0][k] = linear_interpolate(
                    self.board[0][0][k], self.board[7][0][k], t
                )
                # Bottom row (y = 7)
                self.board[i][7][k] = linear_interpolate(
                    self.board[0][7][k], self.board[7][7][k], t
                )

        # 2) Interpolating inner points
        for x in range(1, 7):
            t_x = x / 7.0
            for y in range(1, 7):
                t_y = y / 7.0
                for z in range(3):
                    self.board[x][y][z] = (linear_interpolate(self.board[0][y][z], self.board[7][y][z], t_x)
                                           + linear_interpolate(self.board[x][0][z], self.board[x][7][z], t_y)
                                           ) / 2.0

    def _interpolate_side_pockets(self) -> None:
        for k in range(3):
            self.side_pockets[0][1][k] = (self.side_pockets[0][0][k] * 2 + self.side_pockets[0][3][k]) / 3.0
            self.side_pockets[1][1][k] = (self.side_pockets[1][0][k] * 2 + self.side_pockets[1][3][k]) / 3.0

            self.side_pockets[0][2][k] = (self.side_pockets[0][0][k] + self.side_pockets[0][3][k] * 2) / 3.0
            self.side_pockets[1][2][k] = (self.side_pockets[1][0][k] + self.side_pockets[1][3][k] * 2) / 3.0

    def _read_file_config(self) -> None:
        if not exists(self.configs_path):
            print("Configuration files are not found. Creating new folder.")
            os.mkdir(self.configs_path)

        configs = os.listdir(self.configs_path)

        if len(configs) == 0:
            print("No configuration files found.")
            print("Calibration should be done from scratch.")
            x, y, z, _ = self.device.get_pose().position
            config: list[list[int]] = [[x, y, z] for _ in range(42)]
            self.base_config = config
            return

        print("\nPlease select file's id\n")
        for file_num, config in enumerate(configs):
            print(f"[{file_num}]: {config}")

        is_correct_input = False
        base_config_name = ""
        while not is_correct_input:
            user_input = int(input("> "))
            if user_input not in range(0, len(configs)):
                print("Please select a correct configuration file.")
            else:
                base_config_name = configs[user_input]
                is_correct_input = True

        base_config_path = self.configs_path + "/" + base_config_name
        config: np.ndarray = np.zeros((42, 3), dtype=float)
        with open(base_config_path, "r") as config_file:
            file_lines = config_file.readlines()
            if len(file_lines) < 42:
                raise ValueError(
                    "Configuration file must contain 42 lines.\nPlease select a correct configuration file."
                )

            for i in range(0, 42):
                positions: list[str] = file_lines[i].split(";")
                config[i] = positions

            self.base_config = config

    def _save_all_field_config(self) -> None:
        print("\nPut name of the file you would like to save configuration in:")
        flush_input()
        config_name = input()
        config_path = self.configs_path + "/" + config_name
        with open(config_path, mode="x") as config_file:
            for i in range(0, 42):
                config_file.write(
                    str(self.base_config[i][0])
                    + ";"
                    + str(self.base_config[i][1])
                    + ";"
                    + str(self.base_config[i][2])
                    + "\n"
                )

    def _save_corners_config(self) -> None:
        print("\nPut name of the file you would like to save configuration in:")
        flush_input()
        config_name = input()
        config_path = self.configs_path + "/" + config_name
        with open(config_path, mode="x") as f:
            for i in range(1, 33):
                x, y = get_coord_from_field_id(i)
                f.write(
                    f"{self.board[x][y][0]};{self.board[x][y][1]};{self.board[x][y][2]}\n"
                )

            for i in range(2):
                for j in range(4):
                    f.write(
                        f"{self.side_pockets[i][j][0]};{self.side_pockets[i][j][1]};{self.side_pockets[i][j][2]}\n"
                    )

            f.write(
                f"{self.dispose_area[0]};{self.dispose_area[1]};{self.dispose_area[2]}\n"
            )
            f.write(f"{self.home_pos[0]};{self.home_pos[1]};{self.home_pos[2]}\n")


if __name__ == "__main__":
    CalibrationController().calibrate()
