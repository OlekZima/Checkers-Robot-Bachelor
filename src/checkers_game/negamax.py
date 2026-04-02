"""Negamax decision engine for the checkers AI.

This module implements the Negamax algorithm with alpha-beta pruning
to determine optimal moves for the computer player in a checkers game.
"""

from __future__ import annotations

import logging
import time
from copy import deepcopy
from typing import List, Optional, Tuple

import numpy as np

from src.checkers_game.checkers_game import CheckersGame
from src.common.enums import Color
from src.common.exceptions import DecisionEngineError

logger = logging.getLogger(__name__)

# Constants
MAX_ASSESSMENT_VALUE = 24
DEFAULT_SEARCH_DEPTH = 10
DRAW_REPETITION_THRESHOLD = 3


class NegamaxDecisionEngine:
    """AI decision engine using the Negamax algorithm with alpha-beta pruning.

    This engine evaluates possible moves by recursively exploring the game tree
    and selecting the move with the highest evaluated score from the computer's
    perspective.
    """

    def __init__(
        self,
        computer_color: Color = Color.ORANGE,
        search_depth: int = DEFAULT_SEARCH_DEPTH,
    ) -> None:
        """Initialize the decision engine.

        Args:
            computer_color: The color assigned to the AI player.
            search_depth: Maximum depth for the game tree search.
        """
        self.computer_color = computer_color
        self.search_depth = search_depth

    def decide_move(self, game: Optional[CheckersGame] = None) -> List[int]:
        """Determine the best move for the current game state.

        Args:
            game: The current game state. If None, a new game is created.

        Returns:
            The optimal move sequence as a list of tile IDs.

        Raises:
            DecisionEngineError: If it's not the computer's turn or game is invalid.
        """
        if game is None:
            game = CheckersGame()

        if game.get_turn_of() is None or game.get_turn_of() != self.computer_color:
            raise DecisionEngineError("It is not the computer's turn to move.")

        # If only one move is available, return it immediately
        possible_moves = game.get_possible_opts()
        if len(possible_moves) == 1:
            chosen_move = possible_moves[0]
            logger.info("Only one move available: %s", chosen_move)
            return chosen_move

        logger.info("Starting Negamax search with depth %d", self.search_depth)
        start_time = time.time()

        chosen_move, score, max_depth_reached = self._negamax(
            game_state=game.get_game_state(),
            draw_log=game.get_draw_criteria_log(),
            depth=self.search_depth,
            alpha=-MAX_ASSESSMENT_VALUE,
            beta=MAX_ASSESSMENT_VALUE,
            perspective=1,
        )

        elapsed = time.time() - start_time
        logger.info(
            "Negamax completed in %.2fs | Move: %s | Score: %d | Max depth: %d",
            elapsed,
            chosen_move,
            score,
            max_depth_reached,
        )

        if chosen_move is None:
            raise DecisionEngineError("No valid move found by the decision engine.")

        return chosen_move

    def _negamax(
        self,
        game_state: np.ndarray,
        draw_log: List[Tuple[Color, np.ndarray]],
        depth: int,
        alpha: float,
        beta: float,
        perspective: int,
    ) -> Tuple[Optional[List[int]], float, int]:
        """Recursive Negamax algorithm with alpha-beta pruning.

        Args:
            game_state: Current board state.
            draw_log: History of states for draw detection.
            depth: Remaining search depth.
            alpha: Alpha value for pruning.
            beta: Beta value for pruning.
            perspective: 1 for maximizing, -1 for minimizing.

        Returns:
            Tuple of (best_move, evaluation_score, max_depth_reached).
        """
        # Determine whose turn it is
        current_color = (
            self.computer_color if perspective == 1 else self._opponent_color()
        )

        # Check for draw by repetition
        if self._is_draw_by_repetition(current_color, game_state, draw_log):
            return None, 0.0, 0

        # Get possible moves for the current player
        possible_moves = CheckersGame.get_color_poss_opts(current_color, game_state)

        # No moves available means loss
        if not possible_moves:
            return None, -float(MAX_ASSESSMENT_VALUE), 0

        # Depth limit reached - evaluate the position
        if depth <= 0:
            return None, perspective * self._evaluate_position(game_state), 0

        # Search child nodes
        best_move: Optional[List[int]] = None
        best_value = -float(MAX_ASSESSMENT_VALUE)
        max_depth = 1

        for move in possible_moves:
            child_state = CheckersGame.get_outcome_of_move(deepcopy(game_state), move)
            child_draw_log = self._extend_draw_log(draw_log, current_color, child_state)

            _, child_value, child_depth = self._negamax(
                game_state=child_state,
                draw_log=child_draw_log,
                depth=depth - 1,
                alpha=-beta,
                beta=-alpha,
                perspective=-perspective,
            )

            max_depth = max(max_depth, child_depth + 1)
            negated_value = -child_value

            if negated_value > best_value:
                best_value = negated_value
                best_move = move

            alpha = max(alpha, best_value)

            # Alpha-beta cutoff
            if alpha >= beta:
                break

        return best_move, best_value, max_depth

    def _evaluate_position(self, game_state: np.ndarray) -> float:
        """Evaluate the board position from the computer's perspective.

        The evaluation is based on piece count, with kings weighted more heavily.
        Positive values favor the computer, negative values favor the opponent.

        Args:
            game_state: Current board state.

        Returns:
            Evaluation score.
        """
        if self.computer_color == Color.ORANGE:
            return float(np.sum(game_state))
        return float(-np.sum(game_state))

    def _is_draw_by_repetition(
        self,
        color: Color,
        game_state: np.ndarray,
        draw_log: List[Tuple[Color, np.ndarray]],
    ) -> bool:
        """Check if the current position has repeated enough times to be a draw.

        Args:
            color: The color whose turn it is.
            game_state: Current board state.
            draw_log: History of states.

        Returns:
            True if the position has repeated DRAW_REPETITION_THRESHOLD times.
        """
        repetition_count = sum(
            1
            for logged_color, logged_state in draw_log
            if logged_color == color and np.array_equal(logged_state, game_state)
        )
        return repetition_count >= DRAW_REPETITION_THRESHOLD

    def _extend_draw_log(
        self,
        draw_log: List[Tuple[Color, np.ndarray]],
        color: Color,
        new_state: np.ndarray,
    ) -> List[Tuple[Color, np.ndarray]]:
        """Create a new draw log with the current state appended.

        Args:
            draw_log: Existing draw log.
            color: The color that just moved.
            new_state: The resulting board state.

        Returns:
            A new draw log with the state appended.
        """
        return draw_log + [(color, deepcopy(new_state))]

    def _opponent_color(self) -> Color:
        """Return the color opposite to the computer's color.

        Returns:
            The opponent's color.
        """
        return Color.BLUE if self.computer_color == Color.ORANGE else Color.ORANGE
