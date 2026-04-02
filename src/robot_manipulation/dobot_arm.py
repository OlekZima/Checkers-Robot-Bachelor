"""Concrete implementation of RobotArm for the Dobot Magician."""

from __future__ import annotations

from typing import Tuple

from pydobotplus import Dobot

from .robot_arm import RobotArm

__all__ = ["DobotArm"]


class DobotArm(RobotArm):
    """Concrete implementation of RobotArm for the Dobot Magician."""

    def __init__(self, port: str) -> None:
        """Initialize the Dobot arm.

        Args:
            port: Serial port identifier for the Dobot device.
        """
        self._device = Dobot(port)

    def move_to(self, x: float, y: float, z: float, wait: bool = True) -> None:
        self._device.move_to(x, y, z, wait=wait)

    def get_pose(self) -> Tuple[float, float, float, float]:
        return self._device.get_pose().position

    def activate_suction(self, enabled: bool) -> None:
        self._device.suck(enabled)

    def clear_alarms(self) -> None:
        self._device.clear_alarms()
