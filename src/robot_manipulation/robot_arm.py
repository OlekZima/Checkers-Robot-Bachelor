"""Abstract base class defining the robot arm interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple

__all__ = ["RobotArm"]


class RobotArm(ABC):
    """Abstract base class defining the robot arm interface.

    This class provides a hardware-agnostic interface for robot arm operations.
    """

    @abstractmethod
    def move_to(self, x: float, y: float, z: float, wait: bool = True) -> None:
        """Move the arm to the specified coordinates.

        Args:
            x: X coordinate.
            y: Y coordinate.
            z: Z coordinate.
            wait: Whether to block until movement completes.
        """

    @abstractmethod
    def get_pose(self) -> Tuple[float, float, float, float]:
        """Get the current pose of the arm.

        Returns:
            Tuple of (x, y, z, r) coordinates.
        """

    @abstractmethod
    def activate_suction(self, enabled: bool) -> None:
        """Activate or deactivate the suction cup.

        Args:
            enabled: True to activate, False to deactivate.
        """

    @abstractmethod
    def clear_alarms(self) -> None:
        """Clear any active alarms on the robot."""
