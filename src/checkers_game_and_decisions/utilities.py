import math
import sys
import termios
from typing import Optional

import numpy as np
import cv2
from src.checkers_game_and_decisions.enum_entities import Color


def get_coord_from_tile_id(
    tile_id: int, color: Optional[Color] = None
) -> tuple[int, int]:
    y, x = divmod((tile_id - 1), 4)
    x *= 2

    if y % 2 == 0:
        x += 1

    if color == Color.ORANGE:
        y = 7 - y
        x = 7 - x

    return x, y


def get_tile_id_from_coord(x_cord: float, y_cord: float) -> int:
    tile_id = y_cord * 4 + 1

    if y_cord % 2 == 1:
        tile_id += x_cord / 2
    else:
        tile_id += (x_cord - 1) / 2

    return int(tile_id)


def linear_interpolate(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def flush_input() -> None:
    termios.tcflush(sys.stdin, termios.TCIOFLUSH)


def get_avg_color(img):
    avg_color = np.mean(img, axis=(0, 1))
    return avg_color.astype(int).tolist()


def list_camera_ports() -> list[int]:
    working_ports = []
    for dev_port in range(10):
        cap = cv2.VideoCapture(dev_port)
        is_reading, img = cap.read()
        if is_reading:
            h, w, _ = img.shape
            print(f"Port {dev_port} is working and reads image ({h} x {w})")
            working_ports.append(dev_port)
        cap.release()
    return working_ports


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


def distance_from_color(bgr_sample, bgr_target) -> float:
    distance = sum((bgr_sample[i] - bgr_target[i]) ** 2 for i in range(3))
    return math.sqrt(distance)


def empty_function(_):
    pass
