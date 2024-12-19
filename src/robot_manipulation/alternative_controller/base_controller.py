from pydobotplus import Dobot
from src.common.exceptions import DobotError


class BaseRobotController:
    """Base class for robot control with common functionalities"""

    def __init__(self, dobot_port: str):
        self.device: Dobot = Dobot(dobot_port)

    def move_arm_safely(self, x: float, y: float, z: float, wait: bool = True):
        """Safe arm movement with error handling"""
        try:
            self.device.clear_alarms()
            self.device.move_to(x, y, z, wait=wait)
        except DobotError as exc:
            print(f"Movement error: {exc}")

    def get_position(self) -> tuple[float, float, float]:
        x, y, z, _ = self.device.get_pose().position
        return x, y, z
