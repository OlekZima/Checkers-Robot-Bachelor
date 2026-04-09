"""Checkers game logic module.

This module implements the rules and state management for a standard game of checkers.
It supports move validation, jump sequences, king promotion, and draw detection.
"""

from __future__ import annotations

from copy import deepcopy
from typing import List, Optional, Tuple

import numpy as np

from src.common.enums import Color, GameStatus
from src.common.exceptions import (
    CheckersGameEndError,
    CheckersGameNotPermittedMoveError,
)
from src.common.utils import (
    grid_coords_to_tile_id,
    tile_id_to_grid_coords,
)

# Constants
BOARD_SIZE = 8
EMPTY_TILE = 0
ORANGE_MAN = 1
BLUE_MAN = -1
ORANGE_KING = 2
BLUE_KING = -2
MAX_DRAW_REPETITIONS = 3


class CheckersGame:
    """Manages the state and rules of a checkers game.

    The board is represented as an 8x8 NumPy array where:
    - 0: Empty tile
    - 1: Orange man
    - -1: Blue man
    - 2: Orange king
    - -2: Blue king

    Coordinates (x, y) map to `game_state[x][y]`.
    Tile IDs are 1-based integers representing the 32 playable squares.
    """

    def __init__(self) -> None:
        """Initialize a new checkers game with standard starting positions."""
        self.game_state: np.ndarray = self._create_initial_board()
        self.turn_of: Color = Color.BLUE
        self.turn_player_opts: List[List[int]] = self.get_color_poss_opts(
            self.turn_of, self.game_state
        )
        self.log: List[List[int]] = []
        self.draw_criteria_log: List[Tuple[Color, np.ndarray]] = [
            (self.turn_of, self.game_state.copy())
        ]
        self.orange_score: int = 0
        self.blue_score: int = 0
        self.status: GameStatus = GameStatus.IN_PROGRESS
        self.winning_player: Optional[Color] = None

    @staticmethod
    def _create_initial_board() -> np.ndarray:
        """Create the initial 8x8 board with pieces in starting positions.

        Returns:
            NumPy array representing the initial board state.
        """
        return np.array(
            [
                [0, 1, 0, 0, 0, -1, 0, -1],
                [1, 0, 1, 0, 0, 0, -1, 0],
                [0, 1, 0, 0, 0, -1, 0, -1],
                [1, 0, 1, 0, 0, 0, -1, 0],
                [0, 1, 0, 0, 0, -1, 0, -1],
                [1, 0, 1, 0, 0, 0, -1, 0],
                [0, 1, 0, 0, 0, -1, 0, -1],
                [1, 0, 1, 0, 0, 0, -1, 0],
            ]
        )

    @classmethod
    def _get_tile_value(cls, tile_id: int, game_state: np.ndarray) -> int:
        """Get the value of a tile by its ID.

        Args:
            tile_id: 1-based tile identifier.
            game_state: Current board state.

        Returns:
            Integer value of the tile (0, 1, -1, 2, -2).
        """
        x, y = tile_id_to_grid_coords(tile_id)
        return int(game_state[x][y])

    @classmethod
    def _get_man_moves(
        cls, tile_id: int, game_state: np.ndarray
    ) -> Optional[List[List[int]]]:
        """Get all possible simple moves for a man piece.

        Args:
            tile_id: ID of the man piece.
            game_state: Current board state.

        Returns:
            List of possible moves, or None if tile doesn't contain a man.
        """
        tile_value = cls._get_tile_value(tile_id, game_state)
        if tile_value not in (ORANGE_MAN, BLUE_MAN):
            return None

        x, y = tile_id_to_grid_coords(tile_id)
        moves = []

        if tile_value == ORANGE_MAN:
            if y + 1 == BOARD_SIZE:
                return None  # Reached end, should be king
            if x - 1 >= 0 and game_state[x - 1][y + 1] == EMPTY_TILE:
                moves.append([tile_id, grid_coords_to_tile_id(x - 1, y + 1)])
            if x + 1 < BOARD_SIZE and game_state[x + 1][y + 1] == EMPTY_TILE:
                moves.append([tile_id, grid_coords_to_tile_id(x + 1, y + 1)])
        else:  # BLUE_MAN
            if y == 0:
                return None  # Reached end, should be king
            if x - 1 >= 0 and game_state[x - 1][y - 1] == EMPTY_TILE:
                moves.append([tile_id, grid_coords_to_tile_id(x - 1, y - 1)])
            if x + 1 < BOARD_SIZE and game_state[x + 1][y - 1] == EMPTY_TILE:
                moves.append([tile_id, grid_coords_to_tile_id(x + 1, y - 1)])

        return moves

    @classmethod
    def _get_king_moves(
        cls, tile_id: int, game_state: np.ndarray
    ) -> Optional[List[List[int]]]:
        """Get all possible simple moves for a king piece.

        Args:
            tile_id: ID of the king piece.
            game_state: Current board state.

        Returns:
            List of possible moves, or None if tile doesn't contain a king.
        """
        tile_value = cls._get_tile_value(tile_id, game_state)
        if tile_value not in (ORANGE_KING, BLUE_KING):
            return None

        x, y = tile_id_to_grid_coords(tile_id)
        moves = []
        directions = [(1, 1), (-1, 1), (-1, -1), (1, -1)]

        for dx, dy in directions:
            x_tmp, y_tmp = x + dx, y + dy
            while (
                0 <= x_tmp < BOARD_SIZE
                and 0 <= y_tmp < BOARD_SIZE
                and game_state[x_tmp][y_tmp] == EMPTY_TILE
            ):
                moves.append([tile_id, grid_coords_to_tile_id(x_tmp, y_tmp)])
                x_tmp += dx
                y_tmp += dy

        return moves

    @classmethod
    def _get_man_jumps(
        cls,
        tile_id: int,
        game_state: np.ndarray,
        current_path: Optional[List[int]] = None,
    ) -> Optional[List[List[int]]]:
        """Recursively find all possible jump sequences for a man piece.

        Args:
            tile_id: ID of the man piece.
            game_state: Current board state.
            current_path: Sequence of tiles visited so far in this jump chain.

        Returns:
            List of complete jump sequences, or None if tile doesn't contain a man.
        """
        if current_path is None:
            current_path = []

        tile_value = cls._get_tile_value(tile_id, game_state)
        if tile_value not in (ORANGE_MAN, BLUE_MAN):
            return None

        x, y = tile_id_to_grid_coords(tile_id)
        start_x, start_y = x, y

        if current_path:
            x, y = tile_id_to_grid_coords(current_path[-1])

        jumps = []
        directions = [(1, 1), (-1, 1), (-1, -1), (1, -1)]

        for dx, dy in directions:
            mid_x, mid_y = x + dx, y + dy
            land_x, land_y = x + 2 * dx, y + 2 * dy

            if not (0 <= land_x < BOARD_SIZE and 0 <= land_y < BOARD_SIZE):
                continue

            mid_tile_id = grid_coords_to_tile_id(mid_x, mid_y)
            if -mid_tile_id in current_path:
                continue  # Already jumped this piece

            mid_value = game_state[mid_x][mid_y]
            if tile_value * mid_value >= 0:
                continue  # Not an opponent piece

            land_value = game_state[land_x][land_y]
            if land_value != EMPTY_TILE and not (
                land_x == start_x and land_y == start_y
            ):
                continue  # Landing spot occupied

            jump_segment = [
                grid_coords_to_tile_id(x, y),
                -mid_tile_id,
                grid_coords_to_tile_id(land_x, land_y),
            ]
            next_path = current_path + jump_segment[1:]

            sub_jumps = cls._get_man_jumps(tile_id, game_state, next_path)

            if not sub_jumps:
                jumps.append(jump_segment)
            else:
                for seq in sub_jumps:
                    jumps.append(jump_segment + seq[1:])

        # Filter to keep only the longest sequences
        if jumps:
            max_len = max(len(s) for s in jumps)
            jumps = [s for s in jumps if len(s) == max_len]

        return jumps

    @classmethod
    def _get_king_jumps(
        cls,
        tile_id: int,
        game_state: np.ndarray,
        current_path: Optional[List[int]] = None,
    ) -> Optional[List[List[int]]]:
        """Recursively find all possible jump sequences for a king piece.

        Args:
            tile_id: ID of the king piece.
            game_state: Current board state.
            current_path: Sequence of tiles visited so far.

        Returns:
            List of complete jump sequences, or None if tile doesn't contain a king.
        """
        if current_path is None:
            current_path = []

        tile_value = cls._get_tile_value(tile_id, game_state)
        if tile_value not in (ORANGE_KING, BLUE_KING):
            return None

        x, y = tile_id_to_grid_coords(tile_id)
        start_x, start_y = x, y

        if current_path:
            x, y = tile_id_to_grid_coords(current_path[-1])

        jumps = []
        directions = [(1, 1), (-1, 1), (-1, -1), (1, -1)]

        for dx, dy in directions:
            # Scan along diagonal to find opponent piece
            scan_x, scan_y = x, y
            while 0 <= scan_x < BOARD_SIZE and 0 <= scan_y < BOARD_SIZE:
                val = game_state[scan_x][scan_y]
                if val != EMPTY_TILE and not (scan_x == start_x and scan_y == start_y):
                    break
                scan_x += dx
                scan_y += dy

            # Check if we found an opponent piece
            if not (0 <= scan_x < BOARD_SIZE and 0 <= scan_y < BOARD_SIZE):
                continue

            mid_x, mid_y = scan_x, scan_y
            mid_tile_id = grid_coords_to_tile_id(mid_x, mid_y)

            if tile_value * game_state[mid_x][mid_y] >= 0:
                continue  # Not opponent
            if -mid_tile_id in current_path:
                continue  # Already jumped

            # Scan for landing spots after opponent
            land_x, land_y = mid_x + dx, mid_y + dy
            while 0 <= land_x < BOARD_SIZE and 0 <= land_y < BOARD_SIZE:
                land_val = game_state[land_x][land_y]
                if land_val != EMPTY_TILE and not (
                    land_x == start_x and land_y == start_y
                ):
                    break

                jump_segment = [
                    grid_coords_to_tile_id(x, y),
                    -mid_tile_id,
                    grid_coords_to_tile_id(land_x, land_y),
                ]
                next_path = current_path + jump_segment[1:]

                sub_jumps = cls._get_king_jumps(tile_id, game_state, next_path)

                if not sub_jumps:
                    jumps.append(jump_segment)
                else:
                    for seq in sub_jumps:
                        jumps.append(jump_segment + seq[1:])

                land_x += dx
                land_y += dy

        if jumps:
            max_len = max(len(s) for s in jumps)
            jumps = [s for s in jumps if len(s) == max_len]

        return jumps

    @classmethod
    def get_color_poss_opts(
        cls, color: Color, game_state: np.ndarray
    ) -> List[List[int]]:
        """Get all possible moves and jumps for a given color.

        Jumps take precedence over simple moves per standard checkers rules.

        Args:
            color: Player color (ORANGE or BLUE).
            game_state: Current board state.

        Returns:
            List of possible move sequences.
        """
        all_moves = []
        all_jumps = []

        for tile_id in range(1, 33):
            x, y = tile_id_to_grid_coords(tile_id)
            val = game_state[x][y]

            if (color == Color.ORANGE and val > 0) or (color == Color.BLUE and val < 0):
                if abs(val) == 1:
                    moves = cls._get_man_moves(tile_id, game_state)
                    jumps = cls._get_man_jumps(tile_id, game_state)
                else:
                    moves = cls._get_king_moves(tile_id, game_state)
                    jumps = cls._get_king_jumps(tile_id, game_state)

                if moves:
                    all_moves.extend(moves)
                if jumps:
                    all_jumps.extend(jumps)

        return all_jumps if all_jumps else all_moves

    @classmethod
    def get_outcome_of_move(cls, game_state: np.ndarray, move: List[int]) -> np.ndarray:
        """Apply a move to a game state and return the resulting state.

        Args:
            game_state: Current board state.
            move: Sequence of tile IDs representing the move.

        Returns:
            New game state after the move.
        """
        new_state = game_state.copy()
        start_tile = move[0]
        end_tile = move[-1]

        x_start, y_start = tile_id_to_grid_coords(start_tile)
        x_end, y_end = tile_id_to_grid_coords(end_tile)

        piece = new_state[x_start][y_start]
        new_state[x_start][y_start] = EMPTY_TILE
        new_state[x_end][y_end] = piece

        # Remove captured pieces
        for tile in move[1:-1]:
            if tile < 0:
                x, y = tile_id_to_grid_coords(-tile)
                new_state[x][y] = EMPTY_TILE

        # King promotion
        if piece == ORANGE_MAN and y_end == BOARD_SIZE - 1:
            new_state[x_end][y_end] = ORANGE_KING
        elif piece == BLUE_MAN and y_end == 0:
            new_state[x_end][y_end] = BLUE_KING

        return new_state

    def get_game_state(self) -> np.ndarray:
        """Return a copy of the current game state."""
        return self.game_state.copy()

    def get_draw_criteria_log(self) -> List[Tuple[Color, np.ndarray]]:
        """Return the log of states used for draw detection."""
        return self.draw_criteria_log

    def get_status(self) -> GameStatus:
        """Return the current game status."""
        return self.status

    def get_winning_player(self) -> Optional[Color]:
        """Return the color of the winning player, or None."""
        return self.winning_player

    def get_points(self) -> Tuple[int, int]:
        """Return the current scores as (orange_score, blue_score)."""
        return self.orange_score, self.blue_score

    def get_possible_opts(self) -> List[List[int]]:
        """Return all possible moves for the current player."""
        return self.turn_player_opts

    def get_possible_outcomes(self) -> List[Tuple[List[int], np.ndarray]]:
        """Return all possible moves and their resulting board states."""
        outcomes = []
        for move in self.turn_player_opts:
            new_state = self.get_outcome_of_move(self.game_state, move)
            outcomes.append((move, new_state))
        return outcomes

    def get_turn_of(self) -> Color:
        """Return the color of the player whose turn it is."""
        return self.turn_of

    def perform_move(self, move: List[int]) -> None:
        """Execute a move and update the game state.

        Args:
            move: Sequence of tile IDs representing the move.

        Raises:
            CheckersGameEndError: If the game has already ended.
            CheckersGameNotPermittedMoveError: If the move is not valid.
        """
        if self.status != GameStatus.IN_PROGRESS:
            raise CheckersGameEndError("Game has already ended.")

        if move not in self.turn_player_opts:
            raise CheckersGameNotPermittedMoveError(f"Move {move} is not permitted.")

        # Update scores for captured pieces
        captured_count = sum(1 for tile in move[1:-1] if tile < 0)
        if self.turn_of == Color.ORANGE:
            self.orange_score += captured_count
        else:
            self.blue_score += captured_count

        # Apply move
        self.game_state = self.get_outcome_of_move(self.game_state, move)
        self.log.append(move)

        # Switch turns
        self.turn_of = Color.BLUE if self.turn_of == Color.ORANGE else Color.ORANGE
        self.turn_player_opts = self.get_color_poss_opts(self.turn_of, self.game_state)

        # Update draw log
        self.draw_criteria_log.append((self.turn_of, self.game_state.copy()))

        # Check for draw
        self._check_draw_conditions()

        # Check for win
        if not self.turn_player_opts:
            self.status = GameStatus.WON
            self.winning_player = (
                Color.BLUE if self.turn_of == Color.ORANGE else Color.ORANGE
            )

    def _check_draw_conditions(self) -> None:
        """Check if the game has ended in a draw based on repetition rules."""
        current_state = self.game_state
        repetitions = sum(
            1
            for color, state in self.draw_criteria_log
            if color == self.turn_of and np.array_equal(state, current_state)
        )
        if repetitions >= MAX_DRAW_REPETITIONS:
            self.status = GameStatus.DRAW
