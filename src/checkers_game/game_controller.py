"""Game controller module for managing the checkers game flow.

This module coordinates the game state, AI decision making, and
move validation based on computer vision input.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from src.checkers_game.checkers_game import CheckersGame
from src.checkers_game.negamax import NegamaxDecisionEngine
from src.common.enums import (
    Color,
    GameReportField,
    GameStatus,
    MoveValidationResult,
)
from src.common.utils import tile_id_to_grid_coords


class GameController:
    """Orchestrates the checkers game, handling AI moves and state updates.

    This class manages the interaction between the game logic, the AI engine,
    and the external state updates provided by computer vision.
    """

    def __init__(self, robot_color: Color, engine_depth: int = 3) -> None:
        """Initialize the game controller.

        Args:
            robot_color: The color assigned to the robot player.
            engine_depth: Search depth for the AI decision engine.
        """
        self.game = CheckersGame()
        self.computer_color = robot_color
        self.decision_engine = NegamaxDecisionEngine(
            computer_color=self.computer_color, search_depth=engine_depth
        )

        # State tracking
        self._planned_move: Optional[List[int]] = None
        self._is_crowning_move: Optional[bool] = None

    def generate_report(self) -> Dict[GameReportField, object]:
        """Generate a comprehensive report of the current game state.

        Returns:
            Dictionary mapping report fields to their current values.
        """
        return {
            GameReportField.GAME_STATE: self.game.get_game_state(),
            GameReportField.POINTS: self.game.get_points(),
            GameReportField.STATUS: self.game.get_status(),
            GameReportField.WINNER: self.game.get_winning_player(),
            GameReportField.OPTIONS: self.game.get_possible_opts(),
            GameReportField.TURN_OF: self.game.get_turn_of(),
            GameReportField.ROBOT_COLOR: self.computer_color,
            GameReportField.ROBOT_MOVE: self._planned_move,
            GameReportField.IS_CROWNED: self._is_crowning_move,
        }

    def update_game_state(
        self, observed_board: np.ndarray, allow_different_robot_moves: bool = False
    ) -> MoveValidationResult:
        """Update the game state based on the observed board from computer vision.

        This method compares the observed board with the expected state,
        validates moves, and triggers AI planning when appropriate.

        Args:
            observed_board: The 8x8 board state detected by CV.
            allow_different_robot_moves: If True, accept any valid robot move
                even if it differs from the planned move.

        Returns:
            MoveValidationResult indicating the outcome of the update.
        """
        is_robot_turn = self.game.get_turn_of() == self.computer_color

        # Normalize states for comparison (CV cannot distinguish kings from men)
        expected_state = self._normalize_state_for_comparison(
            self.game.get_game_state()
        )
        observed_rotated = np.rot90(observed_board, 2)

        # Check if the board state has changed
        if self._states_match(observed_board, expected_state, observed_rotated):
            if is_robot_turn:
                self._ensure_move_is_planned()
                return MoveValidationResult.NO_ROBOT_MOVE
            return MoveValidationResult.NO_OPPONENT_MOVE

        # Validate the move performed
        move_performed = self._find_matching_move(observed_board, observed_rotated)

        if move_performed is None:
            return (
                MoveValidationResult.INVALID_ROBOT_MOVE
                if is_robot_turn
                else MoveValidationResult.INVALID_OPPONENT_MOVE
            )

        # Execute the move
        if is_robot_turn:
            return self._handle_robot_move(move_performed, allow_different_robot_moves)
        else:
            return self._handle_opponent_move(move_performed)

    def _normalize_state_for_comparison(self, state: np.ndarray) -> np.ndarray:
        """Convert king pieces to men for comparison with CV output.

        Computer vision often cannot distinguish between kings and regular pieces,
        so we normalize the internal state to treat kings as men for comparison.

        Args:
            state: The internal game state matrix.

        Returns:
            A copy of the state with kings converted to men.
        """
        normalized = state.copy()
        normalized[normalized == 2] = 1  # Orange king -> Orange man
        normalized[normalized == -2] = -1  # Blue king -> Blue man
        return normalized

    def _states_match(
        self,
        observed: np.ndarray,
        expected: np.ndarray,
        observed_rotated: np.ndarray,
    ) -> bool:
        """Check if the observed board matches the expected state.

        Args:
            observed: Raw observed board.
            expected: Expected board (normalized).
            observed_rotated: Observed board rotated 180 degrees.

        Returns:
            True if states match, False otherwise.
        """
        return np.array_equal(observed, expected) or np.array_equal(
            observed_rotated, expected
        )

    def _find_matching_move(
        self, observed: np.ndarray, observed_rotated: np.ndarray
    ) -> Optional[List[int]]:
        """Find the move that results in the observed board state.

        Args:
            observed: Raw observed board.
            observed_rotated: Observed board rotated 180 degrees.

        Returns:
            The move sequence if found, otherwise None.
        """
        possible_outcomes = self.game.get_possible_outcomes()

        for move, outcome_state in possible_outcomes:
            normalized_outcome = self._normalize_state_for_comparison(outcome_state)
            if self._states_match(observed, normalized_outcome, observed_rotated):
                return move

        return None

    def _ensure_move_is_planned(self) -> None:
        """Plan a move if one hasn't been planned yet."""
        if self._planned_move is None or self._is_crowning_move is None:
            self._planned_move = self.decision_engine.decide_move(self.game)
            self._is_crowning_move = self._check_if_crowning_move(self._planned_move)

    def _check_if_crowning_move(self, move: List[int]) -> bool:
        """Determine if a move results in a king promotion.

        Args:
            move: The move sequence to check.

        Returns:
            True if the move results in crowning, False otherwise.
        """
        if not move:
            return False

        destination_tile = move[-1]
        start_x, start_y = tile_id_to_grid_coords(move[0])
        piece_value = self.game.get_game_state()[start_x][start_y]

        is_blue_crowning = (
            self.computer_color == Color.BLUE
            and destination_tile in [1, 2, 3, 4]
            and piece_value == -1
        )
        is_orange_crowning = (
            self.computer_color == Color.ORANGE
            and destination_tile in [29, 30, 31, 32]
            and piece_value == 1
        )

        return is_blue_crowning or is_orange_crowning

    def _handle_robot_move(
        self, move: List[int], allow_different: bool
    ) -> MoveValidationResult:
        """Process a move made by the robot.

        Args:
            move: The move sequence performed.
            allow_different: Whether to accept moves different from the plan.

        Returns:
            MoveValidationResult indicating success or deviation.
        """
        if move == self._planned_move:
            self.game.perform_move(move)
            self._planned_move = None
            self._is_crowning_move = None
            return MoveValidationResult.VALID_RIGHT_ROBOT_MOVE

        if allow_different:
            self.game.perform_move(move)
            self._planned_move = None
            self._is_crowning_move = None

        return MoveValidationResult.VALID_WRONG_ROBOT_MOVE

    def _handle_opponent_move(self, move: List[int]) -> MoveValidationResult:
        """Process a move made by the opponent and plan the robot's response.

        Args:
            move: The opponent's move sequence.

        Returns:
            MoveValidationResult indicating a valid opponent move.
        """
        self.game.perform_move(move)

        if self.game.get_status() == GameStatus.IN_PROGRESS:
            self._planned_move = self.decision_engine.decide_move(self.game)
            self._is_crowning_move = self._check_if_crowning_move(self._planned_move)
        else:
            self._planned_move = None
            self._is_crowning_move = None

        return MoveValidationResult.VALID_OPPONENT_MOVE
