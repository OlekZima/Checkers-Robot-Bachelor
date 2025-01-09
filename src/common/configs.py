"""This module contains dataclasses for the project."""

from dataclasses import dataclass
from typing import Tuple, TypedDict


class ColorConfig(TypedDict):
    orange: Tuple[int, int, int]
    blue: Tuple[int, int, int]
    black: Tuple[int, int, int]
    white: Tuple[int, int, int]


@dataclass
class RecognitionConfig:
    min_area: int = 150
    area_margin_percent: int = 20
    approx_peri_fraction: float = 0.03
    px_dist_to_join: float = 15.0
    threshold1: int = 140
    threshold2: int = 255
    kernel_size: Tuple[int, int] = (2, 2)
    color_dist_threshold: int = 60

    radius: int = 4
