from serial.tools import list_ports
from pydobotplus import Dobot
import numpy as np
import cv2 as cv
import pathlib


class DobotController:

    @classmethod
    def get_xy_from_id(cls, field_id: int):
        y = (field_id - 1) // 4
        x = ((field_id - 1) % 4) * 2 + (1 if y % 2 == 0 else 0)
        return x, y

    def __init__(self):
        self.device = self.connect_to_dobot()
        self.board = np.zeros((8, 8, 3), dtype=float)
        self.side_pockets = np.zeros((2, 4, 3), dtype=float)
        self.dispose_area = np.zeros(3, dtype=float)
        self.home_pos = np.zeros(3, dtype=float)

        self.default_calibration_positions = [
            [244, 51.5, -11],
            [241, -70, -16],
            [67, 47, -5],
            [66, -47, -6],
            [243, 106.5, -18.5],
            [76, 79, 9],
            [240, -106, 1.75],
            [88, -86, 0],
            [130, -150, 3],
            [90, -140, 0],
        ]

        self.calibrate()
        print("Controller created")

    def connect_to_dobot(self):
        available_ports = list_ports.comports()
        print("\nPlease select port by index")
        for i, p in enumerate(available_ports):
            print(f"[{i}]: {p}")
        port_idx = int(input())
        port = available_ports[port_idx].device
        return Dobot(port=port)

    def keyboard_move_dobot(self, increment=1.0):
        x, y, z, _ = self.device.get_pose().position
        instruction_frame = np.zeros((300, 300))  # TODO - instruction how to use frame

        while True:
            self.move_arm(x, y, z)
            cv.imshow("Calibrate instruction", instruction_frame)
            key = cv.waitKey(0)

            x, y, z, _ = self.device.get_pose().position

            if key == 13:  # Enter
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
                exit(2)

        cv.destroyAllWindows()

    def calibrate(self, height=10):
        for idx, position in enumerate(self.default_calibration_positions):
            self.move_arm(*position[:2], position[2] + height)
            print(
                f"Please place the dobot tool on calibration point {idx + 1} and press enter"
            )
            self.move_arm(*position)
            self.keyboard_move_dobot()
            x, y, z, _ = self.device.get_pose().position

            if idx < 4:  # For board corners
                self.board[self.get_board_index(idx)] = [x, y, z]
            elif idx < 8:  # For side pockets
                self.side_pockets[(idx - 4) // 4][(idx - 4) % 4] = [x, y, z]
            elif idx == 8:  # Dispose area
                self.dispose_area = [x, y, z]
            elif idx == 9:  # Home position
                self.home_pos = [x, y, z]

            print(f"x = {x}\ty = {y}\tz = {z}")
            self.move_arm(x, y, z + height)

        self.interpolate_board_fields()
        self.interpolate_side_pockets()

    def get_board_index(self, idx):
        return [(0, 0), (7, 0), (0, 7), (7, 7)][idx]

    def move_arm(self, x, y, z, wait=True):
        try:
            self.device.move_to(x, y, z, wait=wait)
        except Exception as e:
            print(e)

    def interpolate_board_fields(self):
        for i in range(1, 7):
            for j in [0, 7]:
                self.interpolate_edge(0, i, j)

            for j in range(1, 7):
                self.interpolate_edge(i, 0, j)

    def interpolate_edge(self, x, i, j):
        self.board[x][i] = [
            self.board[x][0][k] + i * (self.board[x][7][k] - self.board[x][0][k]) / 7.0
            for k in range(3)
        ]

    def interpolate_side_pockets(self):
        for i in range(2):
            for j in range(4):
                if j in [1, 2]:
                    self.side_pockets[i][j] = [
                        (
                            (
                                self.side_pockets[i][0][k] * 2
                                + self.side_pockets[i][3][k]
                            )
                            / 3.0
                            if j == 1
                            else (
                                self.side_pockets[i][0][k]
                                + self.side_pockets[i][3][k] * 2
                            )
                            / 3.0
                        )
                        for k in range(3)
                    ]


if __name__ == "__main__":
    dobot = DobotController()
    filename = input("\nPut name of the file you would like to save configuration in:")
    pathlib.Path("./configuration_files/").mkdir(parents=True, exist_ok=True)

    with open(f"./configuration_files/{filename}", "w") as f:
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
