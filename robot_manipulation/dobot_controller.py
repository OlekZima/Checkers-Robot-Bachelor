# https://github.com/sammydick22/pydobotplus

from serial.tools import list_ports
from pydobotplus import Dobot
import numpy as np
import cv2 as cv

from os.path import exists
import os

from checkers_game_and_decissions.checkers_game import Color


class DobotController:

    @classmethod
    def get_xy_from_id(cls, id, color):
        y = int((id - 1) / 4)

        x = ((id - 1) % 4) * 2
        if y % 2 == 0:
            x += 1

        if color == Color.RED:
            y = 7 - y
            x = 7 - x

        return x, y

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

        (x, y, z, r) = self.device.get_pose().position
        print(f"\nx:{x} y:{y} z:{z} r:{r}")

        # self.device.suck(True)
        # self.device.move_to(x,y,z+40,r)
        # self.device.move_to(x,y-40,z+40,r)
        # self.device.move_to(x,y+40,z+40,r)
        # self.device.move_to(x,y,z+40,r)
        # self.device.move_to(x,y,z+5,r)
        # self.device.suck(False)

        # Calibrating for board

        # Board field numerating convention:
        #  upper_left = [0][0]
        #  upper_right = [7][0]
        #  bottom_left = [0][7]
        #  bottom_right = [7][7]
        self.board = np.zeros(shape=(8, 8, 3), dtype=float)
        self.side_pockets = np.zeros(shape=(2, 4, 3), dtype=float)
        self.dispose_area = np.zeros(shape=(3), dtype=float)
        self.home_pos = np.zeros(shape=(3), dtype=float)
        self.kings_available = 8

        self.calibrate()

        self.move_arm(
            self.home_pos[0], self.home_pos[1], self.home_pos[2],  wait=True
        )

        print("\nController created\n")

    def keyboard_move_dobot(self, increment=1.0):
        (x, y, z, r) = self.device.get_pose().position

        instruction_frame = np.zeros(
            shape=(300, 300)
        )  # TODO - instruction how to use frame

        while True:
            self.move_arm(x, y, z,  wait=True)

            cv.imshow("Calibrate instruction", instruction_frame)

            key = cv.waitKey(0)

            (x, y, z, r) = self.device.get_pose().position

            if key == 13:
                break
            elif key == ord("w"):
                # y += increment
                x += increment
            elif key == ord("s"):
                # y -= increment
                x -= increment
            elif key == ord("a"):
                # x -= increment
                y += increment
            elif key == ord("d"):
                y -= increment
            elif key == ord("q"):
                z -= increment
            elif key == ord("e"):
                z += increment

        cv.destroyAllWindows()

    def calibrate(self, height=10):

        if exists("robot_manipulation/configuration_files"):
            configs = os.listdir("robot_manipulation/configuration_files")
            print("\nPlease choose a robot position configuration file by id\n")
            for id, c in enumerate(configs):
                print(f"[{id}]: {c}")

            while True:
                user_input = int(input())
                if user_input in range(0, len(configs), 1):
                    base_file = configs[user_input]
                    break

            f = open("robot_manipulation/configuration_files/" + base_file, "r")
            lines = f.readlines()
            f.close()
            if len(lines) < 42:
                raise Exception("Wrong file")

            for i in range(0, 32, 1):
                pos_xyz = lines[i].split(";")
                x, y = DobotController.get_xy_from_id(i + 1, Color.GREEN)
                self.board[x][y][0] = float(pos_xyz[0])
                self.board[x][y][1] = float(pos_xyz[1])
                self.board[x][y][2] = float(pos_xyz[2])

            for i in range(32, 36, 1):
                pos_xyz = lines[i].split(";")
                self.side_pockets[0][i - 32][0] = float(pos_xyz[0])
                self.side_pockets[0][i - 32][1] = float(pos_xyz[1])
                self.side_pockets[0][i - 32][2] = float(pos_xyz[2])

            for i in range(36, 40, 1):
                pos_xyz = lines[i].split(";")
                self.side_pockets[1][i - 36][0] = float(pos_xyz[0])
                self.side_pockets[1][i - 36][1] = float(pos_xyz[1])
                self.side_pockets[1][i - 36][2] = float(pos_xyz[2])

            pos_xyz = lines[40].split(";")
            self.dispose_area[0] = float(pos_xyz[0])
            self.dispose_area[1] = float(pos_xyz[1])
            self.dispose_area[2] = float(pos_xyz[2])

            pos_xyz = lines[41].split(";")
            self.home_pos[0] = float(pos_xyz[0])
            self.home_pos[1] = float(pos_xyz[1])
            self.home_pos[2] = float(pos_xyz[2])

            print("\nDobot calibrated from file: " + base_file + "\n")

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
                        self.device.move_to(
                            x_tmp + 1, y_tmp + 1, z_tmp + 1, wait=True
                        )
                        self.device.move_to(x, y, z - 1, wait=wait)
                        print("\nRetry Successful\n")
                        break
                    except:
                        print("\nRetry Failed\n")
                    retry_cnt += 1
            print("\n==========\n")

    def interpolate_board_fields(self):

        # 1) Interpolating border fields coordinates
        for i in range(1, 7, 1):

            # 1.1) Left column (x = 0)
            self.board[0][i][0] = (
                self.board[0][0][0]
                + i * (self.board[0][7][0] - self.board[0][0][0]) / 7.0
            )
            self.board[0][i][1] = (
                self.board[0][0][1]
                + i * (self.board[0][7][1] - self.board[0][0][1]) / 7.0
            )
            self.board[0][i][2] = (
                self.board[0][0][2]
                + i * (self.board[0][7][2] - self.board[0][0][2]) / 7.0
            )

            # 1.2) Right column (x = 7)
            self.board[7][i][0] = (
                self.board[7][0][0]
                + i * (self.board[7][7][0] - self.board[7][0][0]) / 7.0
            )
            self.board[7][i][1] = (
                self.board[7][0][1]
                + i * (self.board[7][7][1] - self.board[7][0][1]) / 7.0
            )
            self.board[7][i][2] = (
                self.board[7][0][2]
                + i * (self.board[7][7][2] - self.board[7][0][2]) / 7.0
            )

            # 1.3 Upper row (y = 0)
            self.board[i][0][0] = (
                self.board[0][0][0]
                + i * (self.board[7][0][0] - self.board[0][0][0]) / 7.0
            )
            self.board[i][0][1] = (
                self.board[0][0][1]
                + i * (self.board[7][0][1] - self.board[0][0][1]) / 7.0
            )
            self.board[i][0][2] = (
                self.board[0][0][2]
                + i * (self.board[7][0][2] - self.board[0][0][2]) / 7.0
            )

            # 1.4 Bottom row (y = 7)
            self.board[i][7][0] = (
                self.board[0][7][0]
                + i * (self.board[7][7][0] - self.board[0][7][0]) / 7.0
            )
            self.board[i][7][1] = (
                self.board[0][7][1]
                + i * (self.board[7][7][1] - self.board[0][7][1]) / 7.0
            )
            self.board[i][7][2] = (
                self.board[0][7][2]
                + i * (self.board[7][7][2] - self.board[0][7][2]) / 7.0
            )

        # 2) Interpolating inner points
        for x in range(1, 7, 1):
            for y in range(1, 7, 1):
                self.board[x][y][0] = (
                    (
                        self.board[0][y][0]
                        + x * (self.board[7][y][0] - self.board[0][y][0]) / 7.0
                    )
                    + (
                        self.board[x][0][0]
                        + y * (self.board[x][7][0] - self.board[x][0][0]) / 7.0
                    )
                ) / 2.0
                self.board[x][y][1] = (
                    (
                        self.board[0][y][1]
                        + x * (self.board[7][y][1] - self.board[0][y][1]) / 7.0
                    )
                    + (
                        self.board[x][0][1]
                        + y * (self.board[x][7][1] - self.board[x][0][1]) / 7.0
                    )
                ) / 2.0
                self.board[x][y][2] = (
                    (
                        self.board[0][y][2]
                        + x * (self.board[7][y][2] - self.board[0][y][2]) / 7.0
                    )
                    + (
                        self.board[x][0][2]
                        + y * (self.board[x][7][2] - self.board[x][0][2]) / 7.0
                    )
                ) / 2.0

    def interpolate_side_pockets(self):

        self.side_pockets[0][1][0] = (
            self.side_pockets[0][0][0] * 2 + self.side_pockets[0][3][0]
        ) / 3.0
        self.side_pockets[0][1][1] = (
            self.side_pockets[0][0][1] * 2 + self.side_pockets[0][3][1]
        ) / 3.0
        self.side_pockets[0][1][2] = (
            self.side_pockets[0][0][2] * 2 + self.side_pockets[0][3][2]
        ) / 3.0

        self.side_pockets[0][2][0] = (
            self.side_pockets[0][0][0] + self.side_pockets[0][3][0] * 2
        ) / 3.0
        self.side_pockets[0][2][1] = (
            self.side_pockets[0][0][1] + self.side_pockets[0][3][1] * 2
        ) / 3.0
        self.side_pockets[0][2][2] = (
            self.side_pockets[0][0][2] + self.side_pockets[0][3][2] * 2
        ) / 3.0

        self.side_pockets[1][1][0] = (
            self.side_pockets[1][0][0] * 2 + self.side_pockets[1][3][0]
        ) / 3.0
        self.side_pockets[1][1][1] = (
            self.side_pockets[1][0][1] * 2 + self.side_pockets[1][3][1]
        ) / 3.0
        self.side_pockets[1][1][2] = (
            self.side_pockets[1][0][2] * 2 + self.side_pockets[1][3][2]
        ) / 3.0

        self.side_pockets[1][2][0] = (
            self.side_pockets[1][0][0] + self.side_pockets[1][3][0] * 2
        ) / 3.0
        self.side_pockets[1][2][1] = (
            self.side_pockets[1][0][1] + self.side_pockets[1][3][1] * 2
        ) / 3.0
        self.side_pockets[1][2][2] = (
            self.side_pockets[1][0][2] + self.side_pockets[1][3][2] * 2
        ) / 3.0

    def perform_move(self, move=[1, 1], is_crown=False, height=10):

        # Grabbing the first piece
        x, y = DobotController.get_xy_from_id(move[0], self.color)
        self.move_arm(
            self.board[x][y][0],
            self.board[x][y][1],
            self.board[x][y][2] + height,
            wait=True,
        )
        self.move_arm(
            self.board[x][y][0], self.board[x][y][1], self.board[x][y][2],  wait=True
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
                x, y = DobotController.get_xy_from_id(move[i], self.color)
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
        x, y = DobotController.get_xy_from_id(move[len(move) - 1], self.color)
        self.move_arm(
            self.board[x][y][0],
            self.board[x][y][1],
            self.board[x][y][2] + height,
            wait=True,
        )
        self.move_arm(
            self.board[x][y][0], self.board[x][y][1], self.board[x][y][2],  wait=True
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
                x, y = DobotController.get_xy_from_id(-move[i], self.color)
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
            x, y = DobotController.get_xy_from_id(move[len(move) - 1], self.color)

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
                0,
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
        self.move_arm(
            self.home_pos[0], self.home_pos[1], self.home_pos[2],  wait=True
        )


if __name__ == "__main__":
    cntrl = DobotController()
    cntrl.perform_move([1])
    cntrl.perform_move([20])
    cntrl.perform_move([32])
