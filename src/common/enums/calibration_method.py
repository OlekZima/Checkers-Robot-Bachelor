"""Enumeration for calibration methods."""

from __future__ import annotations

from enum import Enum

__all__ = ["CalibrationMethod"]


class CalibrationMethod(Enum):
    """Represents the calibration strategy for the robot arm.

    Attributes:
        CORNER: Calibrate using 4 board corners and interpolate intermediate positions.
        ALL: Manually calibrate each of the 42 positions individually.
    """

    CORNER = 1
    ALL = 2
