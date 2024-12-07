"""This module contains dataclasses for the project."""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class ContourParams:
    """Helper class for storing parameters for the ContourProcessor class.

    Attributes:
        min_area (int): minimal area of the contour
        area_margin (int): margin for the area of the contour
        approx_peri_fraction (float): fraction of the perimeter for the approxPolyDP method
        px_dist_to_join (float): distance between points to join them
        threshold1 (int): first threshold for the Canny method
        threshold2 (int): second threshold for the Canny method
        kernel_size (Tuple[int, int]): size of the kernel for the dilate method
    """

    min_area: int = 150
    area_margin_percent: int = 20
    approx_peri_fraction: float = 0.03
    px_dist_to_join: float = 15.0
    threshold1: int = 140
    threshold2: int = 255
    kernel_size: Tuple[int, int] = (2, 2)
