import math
import sys
import termios
from pathlib import Path
from collections.abc import Sequence
from typing import Optional, Tuple

import cv2 as cv
import numpy as np

from src.common.enums import Color

TWO_PI: float = 2.0 * np.pi
QUARTER_PI: float = np.pi / 4.0
HALF_PI: float = np.pi / 2.0
THREE_QUARTER_PI: float = 3.0 * np.pi / 4.0

CONFIG_PATH: Path = Path("configs")


def get_coord_from_tile_id(
    tile_id: int, color: Optional[Color] = None
) -> Tuple[int, int]:
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


def get_avg_color(img: np.ndarray) -> tuple[int, int, int]:
    avg_color = np.mean(img, axis=(0, 1))
    avg_color_list = avg_color.astype(int).tolist()
    return (avg_color_list[0], avg_color_list[1], avg_color_list[2])


def list_camera_ports() -> list[int]:
    working_ports = []
    for dev_port in range(10):
        cap = cv.VideoCapture(dev_port)
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


def get_avg_pos(points: Optional[Sequence[Sequence[int]]] = None) -> tuple[int, int]:
    """Calculate average position of points

    Args:
        points: List of List of [x,y] coordinates

    Returns:
        Point: Average position as Point object
    """
    if points is None or not points:
        return 0, 0

    x_avg = sum(p[0] for p in points) // len(points)
    y_avg = sum(p[1] for p in points) // len(points)

    return x_avg, y_avg


def distance_from_color(
    bgr_sample: tuple[int, int, int], bgr_target: tuple[int, int, int]
) -> float:
    distance = sum((bgr_sample[i] - bgr_target[i]) ** 2 for i in range(3))
    return math.sqrt(distance)


def empty_function(_):
    pass


def normalize_angle(angle: float) -> float:
    """Normalizes the angle to be in the range [0, 2 * pi).

    Args:
        angle (float):
            Angle in radians.

    Returns:
        float:
            Normalized angle in radians.
    """
    if angle < 0:
        return angle + TWO_PI
    if angle >= TWO_PI:
        return angle - TWO_PI

    return angle
