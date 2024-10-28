from serial.tools import list_ports
from pydobotplus import Dobot
import numpy as np
import cv2 as cv


class DobotController:

    @classmethod
    def get_xy_from_id(cls, id):
        y = int((id - 1) / 4)

        x = ((id - 1) % 4) * 2
        if y % 2 == 0:
            x += 1

        return x, y

    def __init__(self):

        # Connecting to DOBOT
        available_ports = list_ports.comports()

        print("\nPlease select port by index")
        for i, p in enumerate(available_ports):
            print(f"[{i}]: {p}")

        port_idx = int(input())

        port = available_ports[port_idx].device

        self.device = Dobot(port=port)

        x, y, z, r = self.device.get_pose().position
        print(f"\nx:{x} y:{y} z:{z} r:{r}")

        self.device.suck(False)

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

        self.default_calibration_positions = [
            [244, 73, -9],  # upper left board corner
            [246, -71, -11],  # upper right board corner
            [77, 54, -4],  # bottom left board corner
            [77, -53, -4],  # bottom right board corner
            [246, 106.5, -8.9],  # upper left side pocket
            [84, 87, -5],  # bottom left side pocket
            [246, -104, -9.2],  # upper right side pocket
            [88, -86, 0],  # bottom right side pocket
            [130, -150, 3],  # disposal area
            [90, -140, 0],  # home position
        ]

        self.calibrate()

        print("Controller created")

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

    def calibrate(self, height=10):

        # Gathering info for 8x8 board
        print(
            "Please place the dobot tool on upper left board corner (from its perspective) and press enter"
        )
        self.move_arm(
            self.default_calibration_positions[0][0],
            self.default_calibration_positions[0][1],
            self.default_calibration_positions[0][2] + height,
            wait=True,
        )

        self.move_arm(
            self.default_calibration_positions[0][0],
            self.default_calibration_positions[0][1],
            self.default_calibration_positions[0][2],
            wait=True,
        )
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.board[0][0][0] = x
        self.board[0][0][1] = y
        self.board[0][0][2] = z

        print(f"x = {x}\ty = {y}\tz = {z}")
        self.move_arm(x, y, z + height, wait=True)

        print(
            "Please place the dobot tool on upper right board corner (from its perspective) and press enter"
        )
        self.move_arm(
            self.default_calibration_positions[1][0],
            self.default_calibration_positions[1][1],
            self.default_calibration_positions[1][2] + height,
            wait=True,
        )

        self.move_arm(
            self.default_calibration_positions[1][0],
            self.default_calibration_positions[1][1],
            self.default_calibration_positions[1][2],
            wait=True,
        )
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.board[7][0][0] = x
        self.board[7][0][1] = y
        self.board[7][0][2] = z

        print(f"x = {x}\ty = {y}\tz = {z}")
        self.move_arm(x, y, z + height, wait=True)

        print(
            "Please place the dobot tool on bottom left board corner (from its perspective) and press enter"
        )
        self.move_arm(
            self.default_calibration_positions[2][0],
            self.default_calibration_positions[2][1],
            self.default_calibration_positions[2][2] + height,
            wait=True,
        )

        self.move_arm(
            self.default_calibration_positions[2][0],
            self.default_calibration_positions[2][1],
            self.default_calibration_positions[2][2],
            wait=True,
        )
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.board[0][7][0] = x
        self.board[0][7][1] = y
        self.board[0][7][2] = z

        print(f"x = {x}\ty = {y}\tz = {z}")
        self.move_arm(x, y, z + height, wait=True)

        print(
            "Please place the dobot tool on bottom right board corner (from its perspective) and press enter"
        )
        self.move_arm(
            self.default_calibration_positions[3][0],
            self.default_calibration_positions[3][1],
            self.default_calibration_positions[3][2] + height,
            wait=True,
        )

        self.move_arm(
            self.default_calibration_positions[3][0],
            self.default_calibration_positions[3][1],
            self.default_calibration_positions[3][2],
            wait=True,
        )
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.board[7][7][0] = x
        self.board[7][7][1] = y
        self.board[7][7][2] = z

        print(f"x = {x}\ty = {y}\tz = {z}")
        self.move_arm(x, y, z + height, wait=True)

        # Gathering info for side pockets
        print(
            "Please place the dobot tool on upper left side pocket (from its perspective) and press enter"
        )
        self.move_arm(
            self.default_calibration_positions[4][0],
            self.default_calibration_positions[4][1],
            self.default_calibration_positions[4][2] + height,
            wait=True,
        )

        self.move_arm(
            self.default_calibration_positions[4][0],
            self.default_calibration_positions[4][1],
            self.default_calibration_positions[4][2],
            wait=True,
        )
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.side_pockets[0][0][0] = x
        self.side_pockets[0][0][1] = y
        self.side_pockets[0][0][2] = z

        print(f"x = {x}\ty = {y}\tz = {z}")
        self.move_arm(x, y, z + height, wait=True)

        print(
            "Please place the dobot tool on bottom left side pocket (from its perspective) and press enter"
        )
        self.move_arm(
            self.default_calibration_positions[5][0],
            self.default_calibration_positions[5][1],
            self.default_calibration_positions[5][2] + height,
            wait=True,
        )

        self.move_arm(
            self.default_calibration_positions[5][0],
            self.default_calibration_positions[5][1],
            self.default_calibration_positions[5][2],
            wait=True,
        )
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.side_pockets[0][3][0] = x
        self.side_pockets[0][3][1] = y
        self.side_pockets[0][3][2] = z

        print(f"x = {x}\ty = {y}\tz = {z}")
        self.move_arm(x, y, z + height, wait=True)

        print(
            "Please place the dobot tool on upper right side pocket (from its perspective) and press enter"
        )
        self.move_arm(
            self.default_calibration_positions[6][0],
            self.default_calibration_positions[6][1],
            self.default_calibration_positions[6][2] + height,
            wait=True,
        )

        self.move_arm(
            self.default_calibration_positions[6][0],
            self.default_calibration_positions[6][1],
            self.default_calibration_positions[6][2],
            wait=True,
        )
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.side_pockets[1][0][0] = x
        self.side_pockets[1][0][1] = y
        self.side_pockets[1][0][2] = z

        print(f"x = {x}\ty = {y}\tz = {z}")
        self.move_arm(x, y, z + height, wait=True)

        print(
            "Please place the dobot tool on bottom right side pocket (from its perspective) and press enter"
        )
        self.move_arm(
            self.default_calibration_positions[7][0],
            self.default_calibration_positions[7][1],
            self.default_calibration_positions[7][2] + height,
            wait=True,
        )

        self.move_arm(
            self.default_calibration_positions[7][0],
            self.default_calibration_positions[7][1],
            self.default_calibration_positions[7][2],
            wait=True,
        )
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.side_pockets[1][3][0] = x
        self.side_pockets[1][3][1] = y
        self.side_pockets[1][3][2] = z

        print(f"x = {x}\ty = {y}\tz = {z}")
        self.move_arm(x, y, z + height, wait=True)

        # Gathering info for dispose area
        print(
            "Please place the dobot tool where you would like it to dispose of pieces and press enter"
        )
        self.move_arm(
            self.default_calibration_positions[8][0],
            self.default_calibration_positions[8][1],
            self.default_calibration_positions[8][2] + height,
            wait=True,
        )

        self.move_arm(
            self.default_calibration_positions[8][0],
            self.default_calibration_positions[8][1],
            self.default_calibration_positions[8][2],
            wait=True,
        )
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.dispose_area[0] = x
        self.dispose_area[1] = y
        self.dispose_area[2] = z

        print(f"x = {x}\ty = {y}\tz = {z}")

        # Gathering info for home pos
        print(
            "Please place the dobot tool where you would like it to have a home/default position"
        )
        self.move_arm(
            self.default_calibration_positions[9][0],
            self.default_calibration_positions[9][1],
            self.default_calibration_positions[9][2] + height,
            wait=True,
        )

        self.move_arm(
            self.default_calibration_positions[9][0],
            self.default_calibration_positions[9][1],
            self.default_calibration_positions[9][2],
            wait=True,
        )
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.home_pos[0] = x
        self.home_pos[1] = y
        self.home_pos[2] = z

        print(f"x = {x}\ty = {y}\tz = {z}")

        # Calculating all fields

        self.interpolate_board_fields()  # Interpolating board fields
        self.interpolate_side_pockets()  # Interpolating side pockets

    def move_arm(self, x, y, z, wait=True):
        try:
            self.device.move_to(x, y, z, wait=wait)
        except Exception as e:
            print(e)

    def interpolate_board_fields(self):

        # 1) Interpolating border fields coordinates
        for i in range(1, 7):

            # 1.1) Left column (x = 0)
            for k in range(3):
                self.board[0][i][k] = (
                    self.board[0][0][k]
                    + i * (self.board[0][7][k] - self.board[0][0][k]) / 7.0
                )

            # 1.2) Right column (x = 7)
            for k in range(3):
                self.board[7][i][k] = (
                    self.board[7][0][k]
                    + i * (self.board[7][7][k] - self.board[7][0][k]) / 7.0
                )

            # 1.3 Upper row (y = 0)
            for k in range(3):
                self.board[i][0][k] = (
                    self.board[0][0][k]
                    + i * (self.board[7][0][k] - self.board[0][0][k]) / 7.0
                )

            # 1.4 Bottom row (y = 7)
            for k in range(3):
                self.board[i][7][k] = (
                    self.board[0][7][k]
                    + i * (self.board[7][7][k] - self.board[0][7][k]) / 7.0
                )

        # 2) Interpolating inner points
        for x in range(1, 7):
            for y in range(1, 7):
                for z in range(1, 3):
                    self.board[x][y][z] = (
                        (
                            self.board[0][y][z]
                            + x * (self.board[7][y][z] - self.board[0][y][z]) / 7.0
                        )
                        + (
                            self.board[x][0][z]
                            + y * (self.board[x][7][z] - self.board[x][0][z]) / 7.0
                        )
                    ) / 2.0

    def interpolate_side_pockets(self):
        for k in range(2):
            self.side_pockets[0][1][k] = (
                self.side_pockets[0][0][k] * 2 + self.side_pockets[0][3][k]
            ) / 3.0

        for k in range(2):
            self.side_pockets[0][2][k] = (
                self.side_pockets[0][0][k] + self.side_pockets[0][3][k] * 2
            ) / 3.0

        for k in range(2):
            self.side_pockets[1][1][k] = (
                self.side_pockets[1][0][k] * 2 + self.side_pockets[1][3][k]
            ) / 3.0

        for k in range(2):
            self.side_pockets[1][2][k] = (
                self.side_pockets[1][0][k] + self.side_pockets[1][3][k] * 2
            ) / 3.0


if __name__ == "__main__":
    dobot = DobotController()

    print("\nPut name of the file you would like to save configuration in:")

    filename = input()

    f = open("robot_manipulation/configuration_files/" + filename, "w+")

    for i in range(1, 33, 1):
        x, y = DobotController.get_xy_from_id(i)
        f.write(
            str(dobot.board[x][y][0])
            + ";"
            + str(dobot.board[x][y][1])
            + ";"
            + str(dobot.board[x][y][2])
            + "\n"
        )

    for i in range(0, 2, 1):
        for j in range(0, 4, 1):
            f.write(
                str(dobot.side_pockets[i][j][0])
                + ";"
                + str(dobot.side_pockets[i][j][1])
                + ";"
                + str(dobot.side_pockets[i][j][2])
                + "\n"
            )

    f.write(
        str(dobot.dispose_area[0])
        + ";"
        + str(dobot.dispose_area[1])
        + ";"
        + str(dobot.dispose_area[2])
        + "\n"
    )

    f.write(
        str(dobot.home_pos[0])
        + ";"
        + str(dobot.home_pos[1])
        + ";"
        + str(dobot.home_pos[2])
        + "\n"
    )

    f.close()
