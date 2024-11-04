import os
from serial.tools import list_ports
from pydobotplus import Dobot
import numpy as np
import cv2

# from checkers_game_and_decissions.Utilities import (
#     get_coord_from_field_id,
#     linear_interpolate,
#     flush_input,
# )


class Calibrator:

    def __init__(self, default: np.ndarray = None) -> None:
        # Connecting to DOBOT
        available_ports = list_ports.comports()
        self.device = self._connect_to_dobot(available_ports)

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

        self.default = default

        selected_method = self.calibrate()
        self._calibrate(selected_method)

    @staticmethod
    def _connect_to_dobot(available_ports):
        print("\nPlease select port by index")
        for i, p in enumerate(available_ports):
            print(f"[{i}]: {p}")

        port_idx = int(input())
        port = available_ports[port_idx].device
        return Dobot(port=port)

    def calibrate(self) -> str:
        is_correct_input = False
        print("Select calibration method (all/corners):")
        while not is_correct_input:
            input_method = input().strip().lower()
            if input_method not in ["all", "cornerns"]:
                print(
                    f"`{input_method}` is not recognized. Select correct calibration method (all/corners):"
                )
            else:
                return input_method

    def _calibrate(self, method: str) -> None:
        if method == "all":
            self._calibrate_all_fields()
        else:
            self._calibrate_corners()

    def _calibrate_all_fields(self, height: float = 10) -> None:
        self.fields_positions = np.zeros((42, 3), dtype=float)
        for i in range(0, 32, 1):
            if self.fields_positions is not None:
                self.move_arm(
                    self.default[i][0],
                    self.default[i][1],
                    self.default[i][2] + height,
                    True,
                )
            self.move_arm(
                self.default[i][0], self.default[i][1], self.default[i][2], True
            )

            print("\nSet to position of id " + str(i + 1))
            self.keyboard_move_dobot()
            x, y, z, _ = self.device.get_pose().position
            self.fields_positions[i][0] = x
            self.fields_positions[i][1] = y
            self.fields_positions[i][2] = z
            self.move_arm(x, y, z + height, True)

        for i in range(32, 36, 1):
            self.keyboard_move_dobot()
            x, y, z, _ = self.device.get_pose().position
            self.fields_positions[i][0] = x
            self.fields_positions[i][1] = y
            self.fields_positions[i][2] = z
            self.move_arm(x, y, z + height, True)

            print("\nSet to side pocket (left) of id " + str(i - 31))
            self.keyboard_move_dobot()
            x, y, z, _ = self.device.get_pose().position
            self.fields_positions[i][0] = x
            self.fields_positions[i][1] = y
            self.fields_positions[i][2] = z
            self.move_arm(x, y, z + height, True)

        for i in range(36, 40, 1):
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

            print("\nSet to side pocket (right) of id " + str(i - 35))
            self.keyboard_move_dobot()
            x, y, z, _ = self.device.get_pose().position
            self.fields_positions[40][0] = x
            self.fields_positions[40][1] = y
            self.fields_positions[40][2] = z
            self.move_arm(x, y, z + height, True)

        if self.default is not None:
            self.move_arm(
                self.default[40][0],
                self.default[40][1],
                self.default[40][2] + height,
                True,
            )
        self.move_arm(
            self.default[40][0], self.default[40][1], self.default[40][2], True
        )

        print("\nSet to dispose area")
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.fields_positions[40][0] = x
        self.fields_positions[40][1] = y
        self.fields_positions[40][2] = z
        self.move_arm(x, y, z + height, True)

        if self.default is not None:
            self.move_arm(
                self.default[41][0],
                self.default[41][1],
                self.default[41][2] + height,
                True,
            )
            self.move_arm(
                self.default[41][0], self.default[41][1], self.default[41][2], True
            )

        print("\nSet to home position")
        self.keyboard_move_dobot()
        x, y, z, _ = self.device.get_pose().position
        self.fields_positions[41][0] = x
        self.fields_positions[41][1] = y
        self.fields_positions[41][2] = z
        self.move_arm(x, y, z + height, True)

        print("\nCalibration done\n")

    def keyboard_move_dobot(self, increment=1.0):
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

    def move_arm(self, x, y, z, wait=True):
        try:
            self.device.move_to(x, y, z, wait=wait)
        except Exception as e:
            print(e)


if __name__ == "__main__":
    calibrator = Calibrator()
