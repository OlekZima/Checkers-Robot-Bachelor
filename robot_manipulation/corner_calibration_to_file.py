import os

from serial.tools import list_ports
from pydobotplus import Dobot
import numpy as np
import cv2 as cv
import sys
import termios


def flush_input():
    termios.tcflush(sys.stdin, termios.TCIFLUSH)


class DobotController:

    @classmethod
    def get_xy_from_id(cls, id):
        y = (id - 1) // 4
        x = ((id - 1) % 4) * 2

        if y % 2 == 0:
            x += 1

        return x, y

    def __init__(self):
        # Connecting to DOBOT
        available_ports = list_ports.comports()
        self.device = self._connect_to_dobot(available_ports)

        # Board field numerating convention:
        #  upper_left = [0][0]
        #  upper_right = [7][0]
        #  bottom_left = [0][7]
        #  bottom_right = [7][7]
        self.board = np.zeros((8, 8, 3), dtype=float)
        self.side_pockets = np.zeros((2, 4, 3), dtype=float)
        self.dispose_area = np.zeros(3, dtype=float)
        self.home_pos = np.zeros(3, dtype=float)
        # self.kings_available = 8

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

        self.calibrate()

        print("Controller created")

    @staticmethod
    def _connect_to_dobot(available_ports):
        print("\nPlease select port by index")
        for i, p in enumerate(available_ports):
            print(f"[{i}]: {p}")

        port_idx = int(input())
        port = available_ports[port_idx].device
        return Dobot(port=port)

    def keyboard_move_dobot(self, increment=1.0):
        x, y, z, _ = self.device.get_pose().position

        instruction_frame = np.zeros(
            shape=(300, 300)
        )  # TODO - instruction how to use frame

        while True:
            self.move_arm(x, y, z, wait=True)
            cv.imshow("Calibrate instruction", instruction_frame)
            key = cv.waitKey(0)

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
                cv.destroyAllWindows()
                exit(1)

        cv.destroyAllWindows()

    def calibrate(self, height: float = 10):
        def calibrate_point(index: int, storage_array: np.ndarray, storage_indices: list, message: str):
            print(message)
            default_pos = self.default_calibration_positions[index]
            # Move to default position plus height
            self.move_arm(
                default_pos[0], default_pos[1], default_pos[2] + height, wait=True
            )
            # Move to default position
            self.move_arm(default_pos[0], default_pos[1], default_pos[2], wait=True)
            # Allow user to fine-tune the position
            self.keyboard_move_dobot()
            # Get current position
            x, y, z, _ = self.device.get_pose().position
            # Store the position
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
            self.move_arm(x, y, z + height, wait=True)

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

        # Calculating all fields

        self.interpolate_board_fields()  # Interpolating board fields
        self.interpolate_side_pockets()  # Interpolating side pockets

    def move_arm(self, x, y, z, wait=True):
        try:
            self.device.move_to(x, y, z, wait=wait)
        except Exception as e:
            print(e)

    @staticmethod
    def linear_interpolate(a, b, t):
        return a + t * (b - a)

    def interpolate_board_fields(self):

        # 1) Interpolating border fields coordinates
        for i in range(1, 7):
            t = i / 7.0
            for k in range(3):
                # 1.1) Left column (x = 0)
                self.board[0][i][k] = self.linear_interpolate(
                    self.board[0][0][k], self.board[0][7][k], t
                )
                # 1.2) Right column (x = 7)
                self.board[7][i][k] = self.linear_interpolate(
                    self.board[7][0][k], self.board[7][7][k], t
                )
                # 1.3 Upper row (y = 0)
                self.board[i][0][k] = self.linear_interpolate(
                    self.board[0][0][k], self.board[7][0][k], t
                )
                # Bottom row (y = 7)
                self.board[i][7][k] = self.linear_interpolate(
                    self.board[0][7][k], self.board[7][7][k], t
                )

        # 2) Interpolating inner points
        for x in range(1, 7):
            t_x = x / 7.0
            for y in range(1, 7):
                t_y = y / 7.0
                for z in range(3):
                    self.board[x][y][z] = (
                        self.linear_interpolate(
                            self.board[0][y][z], self.board[7][y][z], t_x
                        )
                        + self.linear_interpolate(
                            self.board[x][0][z], self.board[x][7][z], t_y
                        )
                    ) / 2.0

    def interpolate_side_pockets(self):
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


if __name__ == "__main__":
    dobot = DobotController()
    print("\nPut name of the file you would like to save configuration in:")
    flush_input()
    filename = input()

    directory = "robot_manipulation/configuration_files/"
    os.makedirs(directory, exist_ok=True)

    with open(os.path.join(directory, filename), mode="w") as f:
        for i in range(1, 33):
            x, y = DobotController.get_xy_from_id(i)
            f.write(
                f"{dobot.board[x][y][0]};{dobot.board[x][y][1]};{dobot.board[x][y][2]}\n"
            )

        for i in range(2):
            for j in range(4):
                f.write(
                    f"{dobot.side_pockets[i][j][0]};{dobot.side_pockets[i][j][1]};{dobot.side_pockets[i][j][2]}\n"
                )

        f.write(
            f"{dobot.dispose_area[0]};{dobot.dispose_area[1]};{dobot.dispose_area[2]}\n"
        )
        f.write(f"{dobot.home_pos[0]};{dobot.home_pos[1]};{dobot.home_pos[2]}\n")
