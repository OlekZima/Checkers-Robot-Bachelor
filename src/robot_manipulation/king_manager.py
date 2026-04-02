"""Manages king piece inventory and placement."""

from __future__ import annotations

from typing import Tuple

from src.checkers_game.checkers_game import Color
from src.common.utils import tile_id_to_grid_coords

from .calibration_data import CalibrationData
from .robot_arm import RobotArm

__all__ = ["KingManager"]


class KingManager:
    """Manages king piece inventory and placement.

    Tracks available king pieces and handles the crown placement sequence.
    """

    def __init__(
        self,
        arm: RobotArm,
        calibration: CalibrationData,
        height_offset: float = 10.0,
    ) -> None:
        """Initialize the king manager.

        Args:
            arm: Robot arm instance.
            calibration: Calibrated position data.
            height_offset: Safety height above the board for movements.
        """
        self._arm = arm
        self._calibration = calibration
        self._height_offset = height_offset
        self._kings_available = 8

    def place_crown(self, tile_id: int) -> None:
        """Place a king crown on the specified tile.

        Args:
            tile_id: Tile identifier where the crown should be placed.

        Raises:
            ValueError: If no king pieces are available.
        """
        if self._kings_available <= 0:
            raise ValueError("No king pieces available for crowning.")

        # Remove the existing piece from the board
        self._remove_piece_from_board(tile_id)

        # Get king piece from side pocket
        pocket_x, pocket_y = self._get_king_pocket_coordinates()
        self._pick_up_king_from_pocket(pocket_x, pocket_y)

        # Place king on the board
        self._place_piece_on_board(tile_id)

        self._kings_available -= 1

    @property
    def kings_remaining(self) -> int:
        """Return the number of available king pieces."""
        return self._kings_available

    def _remove_piece_from_board(self, tile_id: int) -> None:
        """Remove the existing piece from the board tile.

        Args:
            tile_id: Tile identifier.
        """
        x, y, z = self._get_tile_coordinates(tile_id)
        self._move_to_safe_position(x, y, z)
        self._arm.move_to(x, y, z, wait=True)
        self._arm.activate_suction(True)
        self._move_to_safe_position(x, y, z)

        dispose = self._calibration.dispose_area
        self._move_to_safe_position(dispose[0], dispose[1], dispose[2])
        self._arm.move_to(dispose[0], dispose[1], dispose[2], wait=True)
        self._arm.activate_suction(False)
        self._move_to_safe_position(dispose[0], dispose[1], dispose[2])

    def _pick_up_king_from_pocket(self, pocket_x: int, pocket_y: int) -> None:
        """Pick up a king piece from the side pocket.

        Args:
            pocket_x: Side pocket row index.
            pocket_y: Side pocket column index.
        """
        pos = self._calibration.side_pockets[pocket_x][pocket_y]
        self._move_to_safe_position(pos[0], pos[1], pos[2])
        self._arm.move_to(pos[0], pos[1], pos[2], wait=True)
        self._arm.activate_suction(True)
        self._move_to_safe_position(pos[0], pos[1], pos[2])

    def _place_piece_on_board(self, tile_id: int) -> None:
        """Place a piece on the board tile.

        Args:
            tile_id: Tile identifier.
        """
        x, y, z = self._get_tile_coordinates(tile_id)
        self._move_to_safe_position(x, y, z)
        self._arm.move_to(x, y, z, wait=True)
        self._arm.activate_suction(False)
        self._move_to_safe_position(x, y, z)

    def _get_king_pocket_coordinates(self) -> Tuple[int, int]:
        """Calculate the side pocket coordinates for the next king piece.

        Returns:
            Tuple of (row, column) indices for the side pocket.
        """
        if self._kings_available > 4:
            return 0, 8 - self._kings_available
        else:
            col = 4 - self._kings_available
            return 1, col if col != 4 else 3

    def _get_tile_coordinates(self, tile_id: int) -> Tuple[float, float, float]:
        """Get XYZ coordinates for a tile ID.

        Args:
            tile_id: Tile identifier.

        Returns:
            Tuple of (x, y, z) coordinates.
        """
        x, y = tile_id_to_grid_coords(tile_id, Color.BLUE)
        pos = self._calibration.board_positions[x][y]
        return pos[0], pos[1], pos[2]

    def _move_to_safe_position(self, x: float, y: float, z: float) -> None:
        """Move to a position with a safety offset in Z.

        Args:
            x: X coordinate.
            y: Y coordinate.
            z: Base Z coordinate.
        """
        self._arm.move_to(x, y, z + self._height_offset, wait=True)
