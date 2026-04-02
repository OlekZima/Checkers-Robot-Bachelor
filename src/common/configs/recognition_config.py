"""Configuration dataclass for board recognition and contour detection."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["RecognitionConfig"]


@dataclass
class RecognitionConfig:
    """Configuration parameters for board recognition and contour detection.

    Attributes:
        min_area: Minimum contour area to consider as a valid tile.
        area_margin_percent: Allowed percentage deviation from median tile area.
        approx_peri_fraction: Fraction of perimeter used for polygon approximation.
        px_dist_to_join: Maximum pixel distance to merge nearby vertices.
        threshold1: Lower threshold for Canny edge detection.
        threshold2: Upper threshold for Canny edge detection.
        kernel_size: Size of the dilation kernel (width, height).
        color_dist_threshold: Maximum Euclidean distance for color matching.
        radius: Radius for color sampling around tile centers.
    """

    min_area: int = 150
    area_margin_percent: int = 20
    approx_peri_fraction: float = 0.03
    px_dist_to_join: float = 15.0
    threshold1: int = 140
    threshold2: int = 255
    kernel_size: tuple[int, int] = (2, 2)
    color_dist_threshold: int = 60
    radius: int = 4
