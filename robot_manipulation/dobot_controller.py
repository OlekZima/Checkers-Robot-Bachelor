from serial.tools import list_ports
from pydobotplus import Dobot
import numpy as np
import cv2 as cv

import os

from checkers_game_and_decissions.checkers_game import Color
from checkers_game_and_decissions.Utilities import get_coord_from_field_id, linear_interpolate


class DobotController:

    def __init__(self, color):

        self.color = color

        # Connecting to DOBOT
        available_ports = list_ports.comports()

        print("\nPlease select robot port by index")
        for i, p in enumerate(available_ports):
            print(f"[{i}]: {p}")

        port_idx = int(input())

        port = available_ports[port_idx].device

        self.device = Dobot(port=port)

        (x, y, z, _) = self.device.get_pose().position
        print(f"\nx:{x} y:{y} z:{z}")

        # Calibrating for board

        # Board field numerating convention:
        #  upper_left = [0][0]
        #  upper_right = [7][0]
        #  bottom_left = [0][7]
        #  bottom_right = [7][7]
        self.board = np.zeros(shape=(8, 8, 3), dtype=float)
        self.side_pockets = np.zeros(shape=(2, 4, 3), dtype=float)
        self.dispose_area = np.zeros(shape=3, dtype=float)
        self.home_pos = np.zeros(shape=3, dtype=float)
        self.kings_available = 8

        self.read_calibration_file()

        self.move_arm(*self.home_pos, wait=True)

        print("\nController created\n")

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

    @staticmethod
    def _get_user_input(config_count):
        while True:
            try:
                user_input = int(input())
                if 0 <= user_input <= config_count:
                    return user_input
            except ValueError:
                print("Invalid input. Please enter a valid number.")

    @staticmethod
    def _display_options(configs: list[str]) -> None:
        print("\nPlease choose a robot position configuration file by id\n")
        for id, c in enumerate(configs):
            print(f"[{id}]: {c}")

    def read_calibration_file(self):
        config_dir = "robot_manipulation/configuration_files"

        if not os.path.exists(config_dir):
            print("Configuration directory does not exist.")
            return

        configs: list[str] = os.listdir(config_dir)
        self._display_options(configs)

        user_input: int = self._get_user_input(len(configs))
        base_file: str = configs[user_input]

        with open(base_file, "r") as f:
            lines: list[str] = f.readlines()

        if len(lines) < 42:
            raise ValueError("Wrong file: not enough positions.")

        self._set_config_positions(lines)

        print("\nDobot calibrated from file: " + base_file + "\n")

    def _set_config_positions(self, lines):
        for i in range(0, 32):
            x, y = get_coord_from_field_id(i + 1, Color.BLUE)
            self.board[x][y] = self._parse_calibration_line(lines[i])

        for i in range(32, 36):
            self.side_pockets[0][i - 32] = self._parse_calibration_line(lines[i])

        for i in range(36, 40):
            self.side_pockets[1][i - 36] = self._parse_calibration_line(lines[i])

        self.dispose_area = self._parse_calibration_line(lines[40])
        self.home_pos = self._parse_calibration_line(lines[41])

    @staticmethod
    def _parse_calibration_line(line: str) -> list[float]:
        return [float(coord) for coord in line.split(";")]

    def move_arm(self, x, y, z, wait=True, retry=True, retry_limit=5):
        try:
            self.device.move_to(x, y, z, wait=wait)
        except Exception as e:
            print("\n==========\nAn error occured while performing move\n")
            if retry:
                retry_cnt = 0
                while retry_cnt < retry_limit:
                    x_tmp, y_tmp, z_tmp, _ = self.device.get_pose().position
                    try:
                        print(f"\nRetrying: {retry_cnt+1}/{retry_limit}")
                        self.device.move_to(x_tmp + 1, y_tmp + 1, z_tmp + 1, wait=True)
                        self.device.move_to(x, y, z - 1, wait=wait)
                        print("\nRetry Successful\n")
                        break
                    except:
                        print("\nRetry Failed\n")
                    retry_cnt += 1
            print("\n==========\n")

    def interpolate_board_fields(self):

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
                    first = linear_interpolate(
                        self.board[0][y][z], self.board[7][y][z], t_x
                    )

                    second = linear_interpolate(
                        self.board[x][0][z], self.board[x][7][z], t_y
                    )

                    self.board[x][y][z] = (first + second) / 2.0

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

    def perform_move(
        self, move: list[int] = None, is_crown: bool = False, height: float = 10
    ):

        # Grabbing the first piece
        if move is None:
            move = [1, 1]
        x, y = get_coord_from_field_id(move[0], self.color)
        self.move_arm(
            self.board[x][y][0],
            self.board[x][y][1],
            self.board[x][y][2] + height,
            wait=True,
        )
        self.move_arm(
            self.board[x][y][0], self.board[x][y][1], self.board[x][y][2], wait=True
        )
        self.device.suck(True)
        self.move_arm(
            self.board[x][y][0],
            self.board[x][y][1],
            self.board[x][y][2] + height,
            wait=True,
        )

        # Mid-move movements
        for i in range(1, len(move) - 1, 1):
            if move[i] > 0:
                x, y = get_coord_from_field_id(move[i], self.color)
                self.move_arm(
                    self.board[x][y][0],
                    self.board[x][y][1],
                    self.board[x][y][2] + height,
                    wait=True,
                )
                self.move_arm(
                    self.board[x][y][0],
                    self.board[x][y][1],
                    self.board[x][y][2],
                    wait=True,
                )
                self.move_arm(
                    self.board[x][y][0],
                    self.board[x][y][1],
                    self.board[x][y][2] + height,
                    wait=True,
                )

        # Finishing movement of my piece
        x, y = get_coord_from_field_id(move[len(move) - 1], self.color)
        self.move_arm(
            self.board[x][y][0],
            self.board[x][y][1],
            self.board[x][y][2] + height,
            wait=True,
        )
        self.move_arm(
            self.board[x][y][0], self.board[x][y][1], self.board[x][y][2], wait=True
        )
        self.device.suck(False)
        self.move_arm(
            self.board[x][y][0],
            self.board[x][y][1],
            self.board[x][y][2] + height,
            wait=True,
        )

        # Removing opponent taken out pieces
        for i in range(1, len(move) - 1, 1):
            if move[i] < 0:
                x, y = get_coord_from_field_id(-move[i], self.color)
                self.move_arm(
                    self.board[x][y][0],
                    self.board[x][y][1],
                    self.board[x][y][2] + height,
                    wait=True,
                )
                self.move_arm(
                    self.board[x][y][0],
                    self.board[x][y][1],
                    self.board[x][y][2],
                    wait=True,
                )
                self.device.suck(True)
                self.move_arm(
                    self.board[x][y][0],
                    self.board[x][y][1],
                    self.board[x][y][2] + height,
                    wait=True,
                )
                self.move_arm(
                    self.dispose_area[0],
                    self.dispose_area[1],
                    self.dispose_area[2],
                    wait=True,
                )
                self.device.suck(False)

        # Changing simple piece for king
        # TODO Restorin kings for rematch and situation where all kings are already used - error
        if is_crown:
            x, y = get_coord_from_field_id(move[len(move) - 1], self.color)

            self.move_arm(
                self.board[x][y][0],
                self.board[x][y][1],
                self.board[x][y][2] + height,
                wait=True,
            )
            self.move_arm(
                self.board[x][y][0],
                self.board[x][y][1],
                self.board[x][y][2],
                wait=True,
            )
            self.device.suck(True)
            self.move_arm(
                self.board[x][y][0],
                self.board[x][y][1],
                self.board[x][y][2] + height,
                wait=True,
            )
            self.move_arm(
                self.dispose_area[0],
                self.dispose_area[1],
                self.dispose_area[2],
                wait=True,
            )
            self.device.suck(False)

            if self.kings_available > 4:
                xk = 0
                yk = 8 - self.kings_available
            else:
                xk = 1
                yk = 4 - self.kings_available
                if yk == 4:
                    yk = 3

            self.move_arm(
                self.side_pockets[xk][yk][0],
                self.side_pockets[xk][yk][1],
                self.side_pockets[xk][yk][2] + height,
                wait=True,
            )
            self.move_arm(
                self.side_pockets[xk][yk][0],
                self.side_pockets[xk][yk][1],
                self.side_pockets[xk][yk][2],
                wait=True,
            )
            self.device.suck(True)
            self.move_arm(
                self.side_pockets[xk][yk][0],
                self.side_pockets[xk][yk][1],
                self.side_pockets[xk][yk][2] + height,
                wait=True,
            )
            self.move_arm(
                self.board[x][y][0],
                self.board[x][y][1],
                self.board[x][y][2] + height,
                wait=True,
            )
            self.move_arm(
                self.board[x][y][0],
                self.board[x][y][1],
                self.board[x][y][2],
                wait=True,
            )
            self.device.suck(False)
            self.move_arm(
                self.board[x][y][0],
                self.board[x][y][1],
                self.board[x][y][2] + height,
                wait=True,
            )

            self.kings_available -= 1

        # Returning to home position
        self.move_arm(self.home_pos[0], self.home_pos[1], self.home_pos[2], wait=True)


if __name__ == "__main__":
    l = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    t = [0, 0, 0]
    l[0] = map(str, t)

    print(l)
