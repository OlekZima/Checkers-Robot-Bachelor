"""Module for detecting checker pieces on the board using vectorized operations."""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from src.common.configs import RecognitionConfig
from src.common.enums import Color

from .board_recognition.board import Board
from .checker import Checker


class CheckerDetector:
    """Detects checker pieces on a detected board using vectorized color analysis.

    This class samples colors from tile centers on the board image and classifies
    them as orange, blue, or empty based on Euclidean distance in BGR color space.
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
        sampled_colors = cls._sample_region_colors(frame, centers)

        # Classify each sampled color
        detected_colors = cls._classify_colors(
            sampled_colors,
            orange_bgr,
            blue_bgr,
            orange_threshold_sq,
            blue_threshold_sq,
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
        frame: np.ndarray, centers: np.ndarray, radius: int = 2
    ) -> np.ndarray:
        """Sample the average BGR color around each center point.

        Uses advanced NumPy indexing to efficiently sample a small region
        around each center and compute the mean color.

        Args:
            frame: The source BGR image of shape (H, W, 3).
            centers: Array of center coordinates of shape (N, 2).
            radius: Radius of the sampling region around each center.

        Returns:
            Array of mean BGR colors of shape (N, 3).
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

        # Reshape to (N, num_pixels, 3) and compute mean per center
        sampled_pixels = sampled_pixels.reshape(len(centers), num_pixels, 3)
        return sampled_pixels.mean(axis=1).astype(np.uint8)

    @staticmethod
    def _classify_colors(
        colors: np.ndarray,
        orange_bgr: Tuple[int, int, int],
        blue_bgr: Tuple[int, int, int],
        orange_threshold_sq: float,
        blue_threshold_sq: float,
    ) -> List[Optional[Color]]:
        """Classify sampled colors into checker colors or empty.

        Computes the squared Euclidean distance between each sampled color
        and the reference orange/blue colors.

        Args:
            colors: Array of sampled BGR colors of shape (N, 3).
            orange_bgr: Reference orange color in BGR format.
            blue_bgr: Reference blue color in BGR format.
            orange_threshold_sq: Squared distance threshold for orange.
            blue_threshold_sq: Squared distance threshold for blue.

        Returns:
            List of Color enums (ORANGE, BLUE) or None for each sampled color.
        """
        if len(colors) == 0:
            return []

        # Convert to float64 for precise distance calculation
        colors_float = colors.astype(np.float64)
        orange_ref = np.array(orange_bgr, dtype=np.float64)
        blue_ref = np.array(blue_bgr, dtype=np.float64)

        # Compute squared Euclidean distances
        orange_distances = np.sum((colors_float - orange_ref) ** 2, axis=1)
        blue_distances = np.sum((colors_float - blue_ref) ** 2, axis=1)

        # Classify based on thresholds
        results: List[Optional[Color]] = []
        for i in range(len(colors)):
            if orange_distances[i] <= orange_threshold_sq:
                results.append(Color.ORANGE)
            elif blue_distances[i] <= blue_threshold_sq:
                results.append(Color.BLUE)
            else:
                results.append(None)

        return results
