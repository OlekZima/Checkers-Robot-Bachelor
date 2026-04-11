"""Utility functions for the checkers robot project.

This module provides a collection of helper functions for coordinate conversion,
image processing, mathematical operations, and system utilities.
"""

from __future__ import annotations

import logging
import math
import sys
import termios
from pathlib import Path
from collections.abc import Sequence
from typing import Optional

import cv2 as cv
import numpy as np

from src.common.enums import Color

logger = logging.getLogger(__name__)

CONFIG_PATH: Path = Path("configs")

TWO_PI: float = 2.0 * np.pi

HALF_PI: float = np.pi / 2.0

QUARTER_PI: float = np.pi / 4.0

THREE_QUARTER_PI: float = 3.0 * np.pi / 4.0


def tile_id_to_grid_coords(
    tile_id: int, player_color: Optional[Color] = None
) -> tuple[int, int]:
    """Convert a 1-based tile ID to 0-based grid coordinates (x, y).

    The board uses a standard 8x8 grid where only dark squares are valid.
    Tile IDs are numbered 1-32.

    Args:
        tile_id: 1-based identifier for the tile (1-32).
        player_color: Optional color to orient coordinates from a specific player's perspective.

    Returns:
        Tuple of (x, y) grid coordinates.
    """
    y, x = divmod(tile_id - 1, 4)
    x *= 2

    if y % 2 == 0:
        x += 1

    if player_color == Color.ORANGE:
        # Flip coordinates for orange player perspective
        y = 7 - y
        x = 7 - x

    return x, y


def grid_coords_to_tile_id(x_coord: int, y_coord: int) -> int:
    """Convert 0-based grid coordinates to a 1-based tile ID.

    Args:
        x_coord: X coordinate on the 8x8 grid.
        y_coord: Y coordinate on the 8x8 grid.

    Returns:
        1-based tile ID (1-32).
    """
    tile_id = y_coord * 4 + 1

    if y_coord % 2 == 1:
        tile_id += x_coord // 2
    else:
        tile_id += (x_coord - 1) // 2

    return int(tile_id)


def lerp(start: float, end: float, t: float) -> float:
    """Linearly interpolate between two values.

    Args:
        start: Starting value.
        end: Ending value.
        t: Interpolation factor (typically 0.0 to 1.0).

    Returns:
        Interpolated value.
    """
    return start + t * (end - start)


def euclidean_distance(pt1: tuple[int, int], pt2: tuple[int, int]) -> float:
    """Calculate the Euclidean distance between two 2D points.

    Args:
        pt1: First point (x, y).
        pt2: Second point (x, y).

    Returns:
        Distance between the points.
    """
    dx = pt1[0] - pt2[0]
    dy = pt1[1] - pt2[1]
    return math.hypot(dx, dy)


def compute_centroid(
    points: Optional[Sequence[Sequence[int]]] = None,
) -> tuple[int, int]:
    """Calculate the integer centroid (average position) of a set of points.

    Args:
        points: Sequence of [x, y] coordinates.

    Returns:
        Tuple of (x, y) representing the centroid. Returns (0, 0) if empty.
    """
    if not points:
        return 0, 0

    x_avg = sum(p[0] for p in points) // len(points)
    y_avg = sum(p[1] for p in points) // len(points)

    return x_avg, y_avg


def normalize_radians(angle: float) -> float:
    """Normalize an angle to the range [0, 2*pi).

    Args:
        angle: Angle in radians.

    Returns:
        Normalized angle in radians.
    """
    if angle < 0:
        return angle + TWO_PI
    if angle >= TWO_PI:
        return angle - TWO_PI
    return angle


def compute_average_bgr_color(image: np.ndarray) -> tuple[int, int, int]:
    """Compute the average BGR color of an image region.

    Args:
        image: NumPy array representing the image region (H, W, 3).

    Returns:
        Tuple of (B, G, R) average color values as integers.
    """
    avg_color = np.mean(image, axis=(0, 1))
    return tuple(avg_color.astype(int))


def convert_bgr_to_hsv(color_bgr: tuple[int, int, int]) -> tuple[int, int, int]:
    """Convert a single BGR color to HSV using OpenCV ranges."""
    bgr = np.uint8([[color_bgr]])
    hsv = cv.cvtColor(bgr, cv.COLOR_BGR2HSV)[0, 0]
    return int(hsv[0]), int(hsv[1]), int(hsv[2])


def compute_average_hsv_color(image: np.ndarray) -> tuple[int, int, int]:
    """Compute the average HSV color of an image region."""
    hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)
    avg_color = np.mean(hsv_image, axis=(0, 1))
    return tuple(avg_color.astype(int))


def euclidean_hsv_distance(
    sample_hsv: tuple[int, int, int], target_hsv: tuple[int, int, int]
) -> float:
    """Calculate the Euclidean distance between two HSV colors.

    Hue is circular in OpenCV (0-179), so the shortest hue difference is used.
    Args:
        sample_hsv: Sample color (H, S, V).
        target_hsv: Target color (H, S, V).

    Returns:
        Euclidean distance in HSV space.
    """
    dh = abs(sample_hsv[0] - target_hsv[0])
    dh = min(dh, 180 - dh)
    ds = sample_hsv[1] - target_hsv[1]
    dv = sample_hsv[2] - target_hsv[2]
    return math.sqrt(dh * dh + ds * ds + dv * dv)


def compute_median_hsv_color(image: np.ndarray) -> tuple[int, int, int]:
    """Compute the median HSV color of an image region.

    Median is more robust to outliers and noise than mean.
    Args:
        image: Image region in BGR format.

    Returns:
        Tuple of (H, S, V) median values.
    """
    if image.size == 0:
        return 0, 0, 0
    hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)
    median_color = np.median(hsv_image.reshape(-1, 3), axis=0)
    return int(median_color[0]), int(median_color[1]), int(median_color[2])


def hue_diff(h1: int, h2: int) -> int:
    """Calculate the shortest hue difference between two hues (0-179 scale).

    Args:
        h1: First hue value.
        h2: Second hue value.

    Returns:
        Shortest circular hue difference.
    """
    diff = abs(h1 - h2)
    return min(diff, 180 - diff)


def matches_hsv_thresholds(
    sample_hsv: tuple[int, int, int],
    target_hsv: tuple[int, int, int],
    hue_tolerance: int = 15,
    sat_min: int = 50,
    val_min: int = 40,
) -> bool:
    """Check if sample color matches target using HSV thresholds (lighting-robust).

    This method is more robust than Euclidean distance because it uses:
    - Hue tolerance (circular difference)
    - Minimum saturation (to avoid dark/gray areas)
    - Minimum brightness (to avoid shadows)

    Args:
        sample_hsv: Sample color (H, S, V).
        target_hsv: Target reference color (H, S, V).
        hue_tolerance: Max hue difference tolerance (default 15, range 0-90).
        sat_min: Minimum saturation threshold (default 50, range 0-255).
        val_min: Minimum value/brightness threshold (default 40, range 0-255).

    Returns:
        True if sample matches target within thresholds, False otherwise.
    """
    if sample_hsv[1] < sat_min or sample_hsv[2] < val_min:
        return False
    return hue_diff(sample_hsv[0], target_hsv[0]) <= hue_tolerance


def flush_stdin() -> None:
    """Flush the standard input buffer."""
    try:
        termios.tcflush(sys.stdin, termios.TCIOFLUSH)
    except termios.error:
        logger.warning("Failed to flush stdin buffer.")


def detect_available_camera_ports(max_port: int = 10) -> list[int]:
    """Scan for available camera ports.

    Args:
        max_port: Maximum port number to scan.

    Returns:
        List of working port indices.
    """
    working_ports: list[int] = []
    for port in range(max_port):
        cap = cv.VideoCapture(port)
        is_open, frame = cap.read()
        if is_open and frame is not None:
            height, width, _ = frame.shape
            logger.info("Port %d is active (%dx%d)", port, width, height)
            working_ports.append(port)
        cap.release()
    return working_ports


def noop_callback(*_args, **_kwargs) -> None:
    """A no-operation callback function for default arguments."""
    pass


# Aliases for backward compatibility
get_coord_from_tile_id = tile_id_to_grid_coords
get_tile_id_from_coord = grid_coords_to_tile_id
linear_interpolate = lerp
