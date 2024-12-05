from typing import List, Optional

from pydobotplus import Dobot

from src.checkers_game_and_decisions.checkers_game import Color
from src.common.utilities import get_coord_from_tile_id
from src.robot_manipulation.alternative_controller.base_controller import (
    BaseRobotController,
)


class DobotController(BaseRobotController):
    """Specific Dobot implementation for checkers game"""

    def __init__(self, device: Dobot, color: Color, config_path: Optional[str] = None):
        super().__init__(device, color, config_path)
        self.kings_available = 8

        # Initial home position setup
        self.move_to_home()

    def perform_move(self, move: List[int], is_crown: bool = False):
        """Complex move execution with piece movement and optional crowning"""
        try:
            self._execute_primary_move(move)

            if is_crown:
                self._crown_piece(move)

            self.move_to_home()
        except Exception as e:
            print(f"Move execution error: {e}")

    def _execute_primary_move(self, move: List[int]):
        """Execute primary move logic"""
        # Initial pick up
        start_x, start_y = get_coord_from_tile_id(move[0], self.color)
        self._move_and_pickup(start_x, start_y)

        # Mid-move movements
        for mid_tile in move[1:-1]:
            if mid_tile > 0:
                x, y = get_coord_from_tile_id(mid_tile, self.color)
                self._navigate_through_point(x, y)

        # Final placement
        end_x, end_y = get_coord_from_tile_id(move[-1], self.color)
        self._move_and_place(end_x, end_y)

        # Remove captured pieces
        self._remove_captured_pieces(move)

    def _move_and_pickup(self, x: int, y: int):
        """Move to position and pick up piece"""
        board_pos = self._board[x][y]
        self._move_arm_safely(
            board_pos[0], board_pos[1], board_pos[2] + self._HEIGHT_OFFSET
        )
        self._move_arm_safely(board_pos[0], board_pos[1], board_pos[2])
        self.device.suck(True)
        self._move_arm_safely(
            board_pos[0], board_pos[1], board_pos[2] + self._HEIGHT_OFFSET
        )

    def _navigate_through_point(self, x: int, y: int):
        """Navigate through intermediate points during move"""
        board_pos = self._board[x][y]
        self._move_arm_safely(
            board_pos[0], board_pos[1], board_pos[2] + self._HEIGHT_OFFSET
        )
        self._move_arm_safely(board_pos[0], board_pos[1], board_pos[2])
        self._move_arm_safely(
            board_pos[0], board_pos[1], board_pos[2] + self._HEIGHT_OFFSET
        )

    def _move_and_place(self, x: int, y: int):
        """Move to final position and place piece"""
        board_pos = self._board[x][y]
        self._move_arm_safely(
            board_pos[0], board_pos[1], board_pos[2] + self._HEIGHT_OFFSET
        )
        self._move_arm_safely(board_pos[0], board_pos[1], board_pos[2])
        self.device.suck(False)
        self._move_arm_safely(
            board_pos[0], board_pos[1], board_pos[2] + self._HEIGHT_OFFSET
        )

    def _remove_captured_pieces(self, move: List[int]):
        """Remove captured pieces during move"""
        for tile in move[1:-1]:
            if tile < 0:
                capture_x, capture_y = get_coord_from_tile_id(-tile, self.color)
                board_pos = self._board[capture_x][capture_y]

                # Capture piece
                self._move_arm_safely(
                    board_pos[0], board_pos[1], board_pos[2] + self._HEIGHT_OFFSET
                )
                self._move_arm_safely(board_pos[0], board_pos[1], board_pos[2])
                self.device.suck(True)
                self._move_arm_safely(
                    board_pos[0], board_pos[1], board_pos[2] + self._HEIGHT_OFFSET
                )

                # Move to disposal
                self._move_arm_safely(
                    self._dispose_area[0], self._dispose_area[1], self._dispose_area[2]
                )
                self.device.suck(False)

    def _crown_piece(self, move: List[int]):
        """Crown a piece and replace with king"""
        if self.kings_available <= 0:
            raise ValueError("No kings available for crowning")

        end_x, end_y = get_coord_from_tile_id(move[-1], self.color)
        board_pos = self._board[end_x][end_y]

        # Remove current piece
        self._move_arm_safely(
            board_pos[0], board_pos[1], board_pos[2] + self._HEIGHT_OFFSET
        )
        self._move_arm_safely(board_pos[0], board_pos[1], board_pos[2])
        self.device.suck(True)
        self._move_arm_safely(
            board_pos[0], board_pos[1], board_pos[2] + self._HEIGHT_OFFSET
        )
        self._move_arm_safely(
            self._dispose_area[0], self._dispose_area[1], self._dispose_area[2]
        )
        self.device.suck(False)

        # Select king from side pocket
        king_x, king_y = self._select_king_from_side_pocket()

        # Place king on board
        self._move_arm_safely(
            board_pos[0], board_pos[1], board_pos[2] + self._HEIGHT_OFFSET
        )
        self._move_arm_safely(board_pos[0], board_pos[1], board_pos[2])
        self.device.suck(False)
        self._move_arm_safely(
            board_pos[0], board_pos[1], board_pos[2] + self._HEIGHT_OFFSET
        )

        self.kings_available -= 1

    def _select_king_from_side_pocket(self) -> tuple[int, int]:
        """Select and retrieve a king from side pocket"""
        xk = 0 if self.kings_available > 4 else 1
        yk = 8 - self.kings_available if xk == 0 else 4 - self.kings_available
        yk = 3 if yk == 4 else yk

        side_pocket_pos = self._side_pockets[xk][yk]

        # Move to and pick up king
        self._move_arm_safely(
            side_pocket_pos[0],
            side_pocket_pos[1],
            side_pocket_pos[2] + self._HEIGHT_OFFSET,
        )
        self._move_arm_safely(
            side_pocket_pos[0], side_pocket_pos[1], side_pocket_pos[2]
        )
        self.device.suck(True)
        self._move_arm_safely(
            side_pocket_pos[0],
            side_pocket_pos[1],
            side_pocket_pos[2] + self._HEIGHT_OFFSET,
        )

        return xk, yk
