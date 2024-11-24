import math
import sys
import termios

import numpy as np
import cv2
from src.checkers_game_and_decissions.enum_entities import Color


def get_coord_from_field_id(field_id: int, color: Color) -> tuple[int, int]:
    y, x = divmod((field_id - 1), 4)
    x *= 2

    if y % 2 == 0:
        x += 1

    if color == Color.ORANGE:
        y = 7 - y
        x = 7 - x

    return x, y


def get_field_id_from_coord(x_cord: float, y_cord: float) -> int:
    field_id = y_cord * 4 + 1

    if y_cord % 2 == 1:
        field_id += x_cord / 2
    else:
        field_id += (x_cord - 1) / 2

    return int(field_id)


def linear_interpolate(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def flush_input():
    termios.tcflush(sys.stdin, termios.TCIOFLUSH)


def get_avg_color(img):
    avg_color = np.mean(img, axis=(0, 1))
    return avg_color.astype(int).tolist()


# def get_board_mask(pts, img_shape, margin=10):
#     center = get_avg_pos(pts)
#
#     for pt in pts:
#         dst = get_pts_dist(pt, center)
#         pt[0] = center[0] + int(float(pt[0] - center[0]) / dst * (dst + margin))
#         pt[1] = center[1] + int(float(pt[1] - center[1]) / dst * (dst + margin))
#
#     pts = np.array(pts)
#     mask = np.zeros(img_shape[:2], dtype="uint8")
#     cv2.fillConvexPoly(mask, pts, 1)
#     return mask


def list_camera_ports() -> tuple[list[int], list[int]]:
    # Test the ports and returns a tuple with the available ports and the ones that are working.

    is_working = True
    dev_port = 0
    working_ports = []
    available_ports = []
    while dev_port < 10:  # is_working:
        camera = cv2.VideoCapture(dev_port)
        if not camera.isOpened():
            # is_working = False
            print("Port %s is not working." % dev_port)
            dev_port += 1
        else:
            is_reading, img = camera.read()
            w = camera.get(3)
            h = camera.get(4)
            if is_reading:
                print(
                    "Port %s is working and reads images (%s x %s)" % (dev_port, h, w)
                )
                working_ports.append(dev_port)
            else:
                print(
                    "Port %s for camera ( %s x %s) is present but does not reads."
                    % (dev_port, h, w)
                )
                available_ports.append(dev_port)
            dev_port += 1
    return available_ports, working_ports


def get_pts_dist(pt1, pt2):
    dx = pt1[0] - pt2[0]
    dy = pt1[1] - pt2[1]

    return math.hypot(dx, dy)


def get_avg_pos(pts=None):
    if pts is None:
        pts = [[0, 0], [0, 0]]

    x_avg = sum(pt[0] for pt in pts) // len(pts)
    y_avg = sum(pt[1] for pt in pts) // len(pts)

    return [x_avg, y_avg]


def empt_fun(a):
    pass
