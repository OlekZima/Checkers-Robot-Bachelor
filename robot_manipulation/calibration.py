import os
from os.path import exists

from serial.tools import list_ports
from pydobotplus import Dobot
import numpy as np
import cv2

from checkers_game_and_decissions.utilities import linear_interpolate, get_coord_from_field_id


class Calibrator:

    def __init__(self, use_base_config: bool = False) -> None:
        # Connecting to DOBOT
        self.base_config = None
        available_ports = list_ports.comports()
        self.device = self._connect_to_dobot(available_ports)

        self.configs_path = "configuration_files"
        os.makedirs(self.configs_path, exist_ok=True)

        self.offset_height: float = 10.0

        self.use_base_config = use_base_config

        self.calibrate()
        print("\nCalibration done\n")

    @staticmethod
    def _connect_to_dobot(available_ports) -> Dobot:
        print("\nPlease select port by index")
        for i, p in enumerate(available_ports):
            print(f"[{i}]: {p}")

        port_idx = int(input())
        port = available_ports[port_idx].device
        return Dobot(port=port)

    def calibrate(self) -> None:
        is_correct_input = False
        input_method = ""
        print("Select calibration method (all/corners):")
        while not is_correct_input:
            input_method = input().strip().lower()
            if input_method not in ["all", "corners"]:
                print(
                    f"`{input_method}` is not recognized. Select correct calibration method (all/corners):"
                )
            else:
                is_correct_input = True

        self._calibrate(input_method)

    def _calibrate(self, method: str) -> None:
        if method == "all":
            self.read_file_config()
            self._calibrate_all_fields()
            self._save_all_field_config()
        else:
            self._calibrate_corners()
            self._save_corners_config()

    def _calibrate_all_fields(self) -> None:
        for i in range(0, 32, 1):
            if self.base_config is not None:
                self.move_arm(
                    self.base_config[i][0],
                    self.base_config[i][1],
                    self.base_config[i][2] + self.offset_height,
                    True,
                )
            self.move_arm(
                self.base_config[i][0],
                self.base_config[i][1],
                self.base_config[i][2],
                True,
            )

            print("\nSet to position of id " + str(i + 1))
            self.keyboard_move_dobot()
            x, y, z, _ = self.device.get_pose().position
            self.base_config[i][0] = x
            self.base_config[i][1] = y
            self.base_config[i][2] = z
            self.move_arm(x, y, z + self.offset_height, True)

        for i in range(32, 36, 1):
            self.keyboard_move_dobot()
            x, y, z, _ = self.device.get_pose().position
            self.base_config[i][0] = x
            self.base_config[i][1] = y
            self.base_config[i][2] = z
            self.move_arm(x, y, z + self.offset_height, True)

            print("\nSet to side pocket (left) of id " + str(i - 31))
            self.keyboard_move_dobot()
            x, y, z, _ = self.device.get_pose().position
            self.base_config[i][0] = x
            self.base_config[i][1] = y
            self.base_config[i][2] = z
            self.move_arm(x, y, z + self.offset_height, True)

        for i in range(36, 40, 1):
            if self.base_config is not None:
                self.move_arm(
                    self.base_config[i][0],
                    self.base_config[i][1],
                    self.base_config[i][2] + self.offset_height,
                    True,
                )
            self.move_arm(
                self.base_config[i][0],
                self.base_config[i][1],
                self.base_config[i][2],
                True,
            )

            print("\nSet to side pocket (right) of id " + str(i - 35))
            self.keyboard_move_dobot()
            x, y, z, _ = self.device.get_pose().position
            self.base_config[40][0] = x
            self.base_config[40][1] = y
            self.base_config[40][2] = z
            self.move_arm(x, y, z + self.offset_height, True)

        if self.base_config is not None:
            self.move_arm(
                self.base_config[40][0],
                self.base_config[40][1],
                self.base_config[40][2] + self.offset_height,
                True,
            )
        self.move_arm(
            self.base_config[40][0],
            self.base_config[40][1],
            self.base_config[40][2],
            True,
        )

        print("\nSet to dispose area")
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.base_config[40][0] = x
        self.base_config[40][1] = y
        self.base_config[40][2] = z
        self.move_arm(x, y, z + self.offset_height, True)

        if self.base_config is not None:
            self.move_arm(
                self.base_config[41][0],
                self.base_config[41][1],
                self.base_config[41][2] + self.offset_height,
                True,
            )
            self.move_arm(
                self.base_config[41][0],
                self.base_config[41][1],
                self.base_config[41][2],
                True,
            )

        print("\nSet to home position")
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.base_config[41][0] = x
        self.base_config[41][1] = y
        self.base_config[41][2] = z
        self.move_arm(x, y, z + self.offset_height, True)

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

        def calibrate_point(
                index: int, storage_array: np.ndarray, storage_indices: list, message: str
        ):
            print(message)
            default_pos = self.default_calibration_positions[index]
            # Move to default position plus height
            self.move_arm(
                default_pos[0],
                default_pos[1],
                default_pos[2] + self.offset_height,
                wait=True,
            )
            self.move_arm(default_pos[0], default_pos[1], default_pos[2], wait=True)
            self.keyboard_move_dobot()
            x, y, z, _ = self.device.get_pose().position

            storage = storage_array
            if storage_indices:
                for idx in storage_indices[:-1]:
                    storage = storage[idx]
                storage_idx = storage_indices[-1]
                storage[storage_idx][:] = [x, y, z]
            else:
                storage[:] = [x, y, z]
            print(f"x = {x}\ty = {y}\tz = {z}")
            # Move the arm back up
            self.move_arm(x, y, z + +self.offset_height, wait=True)

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
            calibrate_point(idx, storage, indices, message)

        self.interpolate_board_fields()
        self.interpolate_side_pockets()

    def keyboard_move_dobot(self, increment=1.0) -> None:
        x, y, z, _ = self.device.get_pose().position

        instruction_frame = np.zeros(
            shape=(300, 300)
        )  # TODO - instruction how to use frame

        while True:
            self.move_arm(x, y, z, wait=True)
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

    def move_arm(self, x, y, z, wait=True) -> None:
        try:
            self.device.clear_alarms()
            self.device.move_to(x, y, z, wait=wait)
        except Exception as e:
            print(e)

    def interpolate_board_fields(self) -> None:
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
                    self.board[x][y][z] = (
                        linear_interpolate(
                            self.board[0][y][z], self.board[7][y][z], t_x
                        )
                        + linear_interpolate(
                            self.board[x][0][z], self.board[x][7][z], t_y
                        )
                    ) / 2.0

    def interpolate_side_pockets(self) -> None:
        for k in range(3):
            self.side_pockets[0][1][k] = (
                self.side_pockets[0][0][k] * 2 + self.side_pockets[0][3][k]
            ) / 3.0
            self.side_pockets[1][1][k] = (
                self.side_pockets[1][0][k] * 2 + self.side_pockets[1][3][k]
            ) / 3.0

            self.side_pockets[0][2][k] = (
                self.side_pockets[0][0][k] + self.side_pockets[0][3][k] * 2
            ) / 3.0
            self.side_pockets[1][2][k] = (
                self.side_pockets[1][0][k] + self.side_pockets[1][3][k] * 2
            ) / 3.0

    def read_file_config(self) -> None:
        if not exists(self.configs_path):
            print("Configuration files are not found. Creating new folder.")
            os.mkdir(self.configs_path)

        configs = os.listdir(self.configs_path)
        print("\nPlease select file's id\n")
        for id, config in enumerate(configs):
            print(f"[{id}]: {config}")

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
                    "Configuration file must containt 42 lines.\nPlease select a correct configuration file."
                )

            for i in range(0, 42):
                positions: list[str] = file_lines[i].split(";")
                config[i] = positions

            self.base_config = config

    def _save_all_field_config(self) -> None:
        print("\nPut name of the file you would like to save configuration in:")
        # flush_input()
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
        # flush_input()
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
    calibrator = Calibrator()
