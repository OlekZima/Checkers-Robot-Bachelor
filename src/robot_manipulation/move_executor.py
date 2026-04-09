"""Executes robot arm movements for checker piece manipulation."""

from __future__ import annotations

from typing import List, Tuple

from src.checkers_game.checkers_game import Color
from src.common.utils import tile_id_to_grid_coords

from .calibration_data import CalibrationData
from .robot_arm import RobotArm

__all__ = ["MoveExecutor"]


class MoveExecutor:
    """Executes robot arm movements for checker piece manipulation.

    Handles the sequence of movements required to pick up, move, and place
    checker pieces on the board.
    """

    def __init__(
        self,
        arm: RobotArm,
        calibration: CalibrationData,
        robot_color: Color,
        height_offset: float = 10.0,
    ) -> None:
        """Initialize the move executor.

        Args:
            arm: Robot arm instance.
            calibration: Calibrated position data.
            robot_color: The color this robot is playing as.
            height_offset: Safety height above the board for movements.
        """
        self._arm = arm
        self._calibration = calibration
        self._robot_color = robot_color
        self._height_offset = height_offset

    def execute_move(self, move_sequence: List[int]) -> None:
        """Execute a complete move sequence.

        Args:
            move_sequence: List of tile IDs representing the move path.
                Positive values indicate own pieces, negative values indicate
                opponent pieces to be removed.

        Raises:
            ValueError: If the move sequence is invalid.
        """
        if not move_sequence or len(move_sequence) < 2:
            raise ValueError("Move sequence must contain at least start and end tiles.")

        self._pick_up_piece(move_sequence[0])
        self._traverse_intermediate_tiles(move_sequence[1:-1])
        self._place_piece(move_sequence[-1])
        self._remove_captured_pieces(move_sequence[1:-1])

    def go_home(self) -> None:
        """Move the arm to the home position."""
        home = self._calibration.home_position
        self._move_to_safe_position(home[0], home[1], home[2])

    def _get_tile_coordinates(self, tile_id: int) -> Tuple[float, float, float]:
        """Get XYZ coordinates for a tile ID.

        Args:
            tile_id: Tile identifier (positive for board positions).

        Returns:
            Tuple of (x, y, z) coordinates.
        """
        x, y = tile_id_to_grid_coords(abs(tile_id), self._robot_color)
        pos = self._calibration.board_positions[x][y]
        return pos[0], pos[1], pos[2]

    def _pick_up_piece(self, tile_id: int) -> None:
        """Pick up a checker piece from the specified tile.

        Args:
            tile_id: Tile identifier.
        """
        x, y, z = self._get_tile_coordinates(tile_id)
        self._move_to_safe_position(x, y, z)
        self._arm.move_to(x, y, z, wait=True)
        self._arm.activate_suction(True)
        self._move_to_safe_position(x, y, z)

    def _place_piece(self, tile_id: int) -> None:
        """Place a checker piece on the specified tile.

        Args:
            tile_id: Tile identifier.
        """
        x, y, z = self._get_tile_coordinates(tile_id)
        self._move_to_safe_position(x, y, z)
        self._arm.move_to(x, y, z, wait=True)
        self._arm.activate_suction(False)
        self._move_to_safe_position(x, y, z)

    def _traverse_intermediate_tiles(self, tile_ids: List[int]) -> None:
        """Move through intermediate tiles in a multi-step move.

        Args:
            tile_ids: List of intermediate tile IDs.
        """
        for tile_id in tile_ids:
            if tile_id > 0:
                x, y, z = self._get_tile_coordinates(tile_id)
                self._move_to_safe_position(x, y, z)
                self._arm.move_to(x, y, z, wait=True)
                self._move_to_safe_position(x, y, z)

    def _remove_captured_pieces(self, tile_ids: List[int]) -> None:
        """Remove opponent pieces captured during the move.

        Args:
            tile_ids: List of tile IDs (negative values indicate captures).
        """
        dispose = self._calibration.dispose_area

        for tile_id in tile_ids:
            if tile_id < 0:
                x, y, z = self._get_tile_coordinates(tile_id)
                self._move_to_safe_position(x, y, z)
                self._arm.move_to(x, y, z, wait=True)
                self._arm.activate_suction(True)
                self._move_to_safe_position(x, y, z)

                self._move_to_safe_position(dispose[0], dispose[1], dispose[2])
                self._arm.move_to(dispose[0], dispose[1], dispose[2], wait=True)
                self._arm.activate_suction(False)
                self._move_to_safe_position(dispose[0], dispose[1], dispose[2])

    def _move_to_safe_position(self, x: float, y: float, z: float) -> None:
        """Move to a position with a safety offset in Z.

        Args:
            x: X coordinate.
            y: Y coordinate.
            z: Base Z coordinate.
        """
        self._arm.move_to(x, y, z + self._height_offset, wait=True)
