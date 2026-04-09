"""Dataclass for storing calibrated robot arm positions."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["CalibrationData"]


@dataclass
class CalibrationData:
    """Stores calibrated positions for the robot arm.

    Attributes:
        board_positions: 3D array of shape (8, 8, 3) containing XYZ coordinates for each board tile.
        side_pockets: 3D array of shape (2, 4, 3) containing XYZ coordinates for king piece storage.
        dispose_area: 1D array of shape (3,) containing XYZ coordinates for the disposal area.
        home_position: 1D array of shape (3,) containing XYZ coordinates for the home position.
    """

    board_positions: np.ndarray = field(default_factory=lambda: np.zeros((8, 8, 3)))
    side_pockets: np.ndarray = field(default_factory=lambda: np.zeros((2, 4, 3)))
    dispose_area: np.ndarray = field(default_factory=lambda: np.zeros(3))
    home_position: np.ndarray = field(default_factory=lambda: np.zeros(3))
