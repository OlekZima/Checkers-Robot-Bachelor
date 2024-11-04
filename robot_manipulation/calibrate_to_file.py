from serial.tools import list_ports
from pydobotplus import Dobot
import numpy as np
import cv2 as cv

from os.path import exists
import os


class DobotController:

    def __init__(self, default: np.ndarray):

        # Connecting to DOBOT
        available_ports = list_ports.comports()

        print("\nPlease select port by index")
        for i, p in enumerate(available_ports):
            print(f"[{i}]: {p}")

        port_idx = int(input())

        port = available_ports[port_idx].device

        self.device = Dobot(port=port)

        x, y, z, _ = self.device.get_pose().position
        print(f"\nx:{x} y:{y} z:{z}")

        self.positions = np.zeros((42, 3), dtype=float)

        self.default = default

        self.calibrate()

    def calibrate(self, height: float = 10):

        for i in range(0, 32, 1):
            self.go_to_next_pos_from_file(height, i)

            print("\nSet to position of id " + str(i + 1))
            self.set_ith_position_manually(i)

        for i in range(32, 36, 1):
            self.go_to_next_pos_from_file(i)

            print("\nSet to side pocket (left) of id " + str(i - 31))
            self.set_ith_position_manually(i)

        for i in range(36, 40, 1):
            self.go_to_next_pos_from_file(i)

            print("\nSet to side pocket (right) of id " + str(i - 35))
            self.set_ith_position_manually(i)

        self.go_to_next_pos_from_file(height, 40)

        print("\nSet to dispose area")
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.positions[40][0] = x
        self.positions[40][1] = y
        self.positions[40][2] = z
        self.move_arm(x, y, z + height, True)

        self.go_to_next_pos_from_file(height, 41)

        print("\nSet to home position")
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.positions[41][0] = x
        self.positions[41][1] = y
        self.positions[41][2] = z
        self.move_arm(x, y, z + height, True)

        print("\nCalibration done\n")

    def go_to_next_pos_from_file(self, i: int, height: int = 10):
        if self.default is not None:
            self.move_arm(
                self.default[i][0],
                self.default[i][1],
                self.default[i][2] + height,
                True,
            )
            self.move_arm(
                self.default[i][0], self.default[i][1], self.default[i][2], True
            )

    def set_ith_position_manually(self, i: int, height: int = 10):
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.positions[i][0] = x
        self.positions[i][1] = y
        self.positions[i][2] = z
        self.move_arm(x, y, z + height, True)

    def keyboard_move_dobot(self, increment: float = 1.0):
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

    def move_arm(self, x: float, y: float, z: float, wait: bool = True):
        try:
            self.device.move_to(x, y, z, wait=wait)
        except Exception as e:
            print(e)


if __name__ == "__main__":

    print("\nWould you like to use base configuration file? [y]/[n]")
    while True:
        user_input = input()
        if user_input == "y":
            use_file = True
            break
        if user_input == "n":
            use_file = False
            break
        print("Wrong input")

    if use_file:
        if exists("robot_manipulation/configuration_files"):
            configs = os.listdir("robot_manipulation/configuration_files")
            print("\nPlease choose a file by id\n")
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

            result_list: np.ndarray = np.zeros((42, 3), dtype=float)
            for i in range(0, 42, 1):
                pos_xyz = lines[i].split(";")
                result_list[i][0] = float(pos_xyz[0])
                result_list[i][1] = float(pos_xyz[1])
                result_list[i][2] = float(pos_xyz[2])

            dobot = DobotController(result_list)

        else:
            raise Exception("No files")

    else:
        dobot = DobotController(None)

    print("\nPut name of the file you would like to save configuration in:")

    filename = input()

    f = open("robot_manipulation/configuration_files/" + filename, "w")

    for i in range(0, 42, 1):
        f.write(
            str(dobot.positions[i][0])
            + ";"
            + str(dobot.positions[i][1])
            + ";"
            + str(dobot.positions[i][2])
            + "\n"
        )

    f.close()
    print("\nDONE!\n")
