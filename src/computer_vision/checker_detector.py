"""Module for detecting checker pieces on the board using vectorized operations."""

from __future__ import annotations

from typing import List, Optional, Tuple

import cv2
import numpy as np

from src.common.configs import RecognitionConfig
from src.common.enums import Color

from .board_recognition.board import Board
from .checker import Checker


class CheckerDetector:
    """Detects checker pieces on a detected board using vectorized color analysis.

    This class samples colors from tile centers on the board image and classifies
    them as orange, blue, or empty based on Euclidean distance in HSV color space.
    """

    @classmethod
    def detect(
        cls,
        board: Board,
        frame: np.ndarray,
        orange_rgb: Tuple[int, int, int] = (255, 165, 0),
        blue_rgb: Tuple[int, int, int] = (0, 0, 255),
        distance_threshold: Optional[int] = None,
    ) -> List[Checker]:
        """Detect checker pieces on the board.

        Args:
            board: The detected board containing tile grid points.
            frame: The source BGR image frame to analyze.
            orange_rgb: Reference RGB color for orange checkers.
            blue_rgb: Reference RGB color for blue checkers.
            distance_threshold: Maximum allowed Euclidean distance for color matching.
                Defaults to the value in RecognitionConfig.

        Returns:
            A list of detected Checker instances.
        """
        threshold = distance_threshold or RecognitionConfig.color_dist_threshold

        # Convert reference colors from RGB to BGR
        orange_bgr = (orange_rgb[2], orange_rgb[1], orange_rgb[0])
        blue_bgr = (blue_rgb[2], blue_rgb[1], blue_rgb[0])

        # Precompute squared distance thresholds
        orange_threshold_sq = threshold**2
        blue_threshold_sq = threshold**2

        # Extract valid tile centers and their corresponding board positions
        centers, positions = cls._extract_tile_centers(board)

        if len(centers) == 0:
            return []

        # Sample colors from the image at each tile center
        config = RecognitionConfig()
        sampled_colors = cls._sample_region_colors(frame, centers, radius=config.radius)

        # Convert sampled colors and references to HSV for distance-based classification
        sampled_hsv = cls._convert_bgr_array_to_hsv(sampled_colors)
        orange_hsv = cls._convert_bgr_to_hsv(orange_bgr)
        blue_hsv = cls._convert_bgr_to_hsv(blue_bgr)

        # Classify each sampled color using HSV thresholds
        detected_colors = cls._classify_colors(
            sampled_hsv,
            orange_hsv,
            blue_hsv,
            orange_threshold_sq,
            blue_threshold_sq,
            hue_tolerance=config.hsv_hue_tolerance,
            sat_min=config.hsv_sat_min,
            val_min=config.hsv_val_min,
        )

        # Build the list of detected checkers
        return [
            Checker(color=color, position=pos)
            for color, pos in zip(detected_colors, positions)
            if color is not None
        ]

    @staticmethod
    def _extract_tile_centers(
        board: Board,
    ) -> Tuple[np.ndarray, List[Tuple[int, int]]]:
        """Calculate the center coordinates for all valid board tiles.

        Args:
            board: The detected board with a 9x9 grid of points.

        Returns:
            A tuple containing:
                - centers: NumPy array of shape (N, 2) with (x, y) coordinates.
                - positions: List of (x, y) grid indices for each center.
        """
        centers: List[Tuple[int, int]] = []
        positions: List[Tuple[int, int]] = []

        grid_points = board.points
        num_rows = len(grid_points) - 1
        num_cols = len(grid_points[0]) - 1 if num_rows > 0 else 0

        for row in range(num_rows):
            for col in range(num_cols):
                tile_corners = [
                    grid_points[row][col],
                    grid_points[row][col + 1],
                    grid_points[row + 1][col + 1],
                    grid_points[row + 1][col],
                ]
                valid_corners = [pt for pt in tile_corners if pt is not None]

                if len(valid_corners) >= 3:
                    center_x = sum(pt[0] for pt in valid_corners) // len(valid_corners)
                    center_y = sum(pt[1] for pt in valid_corners) // len(valid_corners)
                    centers.append((center_x, center_y))
                    positions.append((row, col))

        if not centers:
            return np.array([], dtype=np.int32), []

        return np.array(centers, dtype=np.int32), positions

    @staticmethod
    def _sample_region_colors(
        frame: np.ndarray, centers: np.ndarray, radius: int = 3
    ) -> np.ndarray:
        """Sample the median BGR color around each center point.

        Uses median instead of mean for robustness to noise and uneven lighting.
        Samples a larger region (default radius=3 gives 7x7 patch).

        Args:
            frame: The source BGR image of shape (H, W, 3).
            centers: Array of center coordinates of shape (N, 2).
            radius: Radius of the sampling region around each center (default 3).

        Returns:
            Array of median BGR colors of shape (N, 3).
        """
        if len(centers) == 0:
            return np.array([], dtype=np.uint8)

        height, width = frame.shape[:2]

        # Create a grid of offsets for the sampling region
        offsets = np.arange(-radius, radius + 1)
        offset_y, offset_x = np.meshgrid(offsets, offsets)
        offset_y = offset_y.ravel()
        offset_x = offset_x.ravel()
        num_pixels = len(offset_y)

        # Extract and clip center coordinates to valid image bounds
        x_coords = np.clip(centers[:, 0], radius, width - 1 - radius)
        y_coords = np.clip(centers[:, 1], radius, height - 1 - radius)

        # Generate absolute pixel coordinates for all samples
        sample_x = (x_coords[:, None] + offset_x[None, :]).ravel()
        sample_y = (y_coords[:, None] + offset_y[None, :]).ravel()

        # Sample all pixels at once using advanced indexing
        sampled_pixels = frame[sample_y, sample_x]

        # Reshape to (N, num_pixels, 3) and compute median per center
        sampled_pixels = sampled_pixels.reshape(len(centers), num_pixels, 3)
        return np.median(sampled_pixels, axis=1).astype(np.uint8)

    @staticmethod
    def _convert_bgr_to_hsv(color_bgr: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Convert a single BGR color tuple to HSV."""
        arr = np.uint8([[color_bgr]])
        hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)[0, 0]
        return int(hsv[0]), int(hsv[1]), int(hsv[2])

    @staticmethod
    def _convert_bgr_array_to_hsv(colors: np.ndarray) -> np.ndarray:
        """Convert an array of BGR colors to HSV."""
        if len(colors) == 0:
            return np.array([], dtype=np.uint8).reshape(0, 3)
        colors_bgr = colors.reshape(-1, 1, 3).astype(np.uint8)
        hsv = cv2.cvtColor(colors_bgr, cv2.COLOR_BGR2HSV).reshape(-1, 3)
        return hsv

    @staticmethod
    def _classify_colors(
        colors: np.ndarray,
        orange_hsv: Tuple[int, int, int],
        blue_hsv: Tuple[int, int, int],
        orange_threshold_sq: float,
        blue_threshold_sq: float,
        hue_tolerance: int = 15,
        sat_min: int = 50,
        val_min: int = 40,
    ) -> List[Optional[Color]]:
        """Classify sampled colors into checker colors or empty using HSV thresholds.

        Uses hue tolerance + saturation/value thresholds for robust classification
        that is lighting-invariant. This approach is more reliable than pure
        Euclidean distance under varying lighting conditions.

        Args:
            colors: Array of sampled HSV colors of shape (N, 3).
            orange_hsv: Reference orange color in HSV format.
            blue_hsv: Reference blue color in HSV format.
            orange_threshold_sq: Unused (kept for backward compatibility).
            blue_threshold_sq: Unused (kept for backward compatibility).
            hue_tolerance: Max hue difference tolerance (default 15).
            sat_min: Minimum saturation threshold (default 50).
            val_min: Minimum value/brightness threshold (default 40).

        Returns:
            List of Color enums (ORANGE, BLUE) or None for each sampled color.
        """
        from src.common.utils import hue_diff

        if len(colors) == 0:
            return []

        results: List[Optional[Color]] = []
        for i in range(len(colors)):
            sample_h, sample_s, sample_v = (
                int(colors[i, 0]),
                int(colors[i, 1]),
                int(colors[i, 2]),
            )

            # Check saturation and brightness constraints first
            if sample_s < sat_min or sample_v < val_min:
                results.append(None)
                continue

            # Check hue match for orange
            if hue_diff(sample_h, orange_hsv[0]) <= hue_tolerance:
                results.append(Color.ORANGE)
            # Check hue match for blue
            elif hue_diff(sample_h, blue_hsv[0]) <= hue_tolerance:
                results.append(Color.BLUE)
            else:
                results.append(None)

        return results
