"""
Module for managing checkers game state and visualization.

This module provides functionality for managing a checkers game state,
including board visualization, game state updates, and state tracking.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import cv2 as cv
import numpy as np

from src.common.configs import ColorConfig
from src.common.enums import Color

from .board_recognition.board import Board
from .board_recognition.board_detector import BoardDetector
from .checker import Checker
from .checker_detector import CheckerDetector


class GameState:
    """Manages the state and visualization of a checkers game.

    This class handles game state tracking, updates from computer vision input,
    and visualization of the current game state.

    Attributes:
        BOARD_SIZE: Size of the checkers board (8x8).
        CELL_SIZE: Pixel size of each board cell in visualization.
        BOARD_OFFSET: Offset from the edge in visualization.
        CHECKER_RADIUS: Radius of checker pieces in visualization.
        BACKGROUND_COLOR: Background color in BGR format.
        DARK_FIELD_COLOR: Color for dark fields in BGR format.
        LIGHT_FIELD_COLOR: Color for light fields in BGR format.
        ORANGE_CHECKER_COLOR: Color for orange checkers in BGR format.
        BLUE_CHECKER_COLOR: Color for blue checkers in BGR format.
        GRID_COLOR: Color for grid lines in BGR format.
        GRID_THICKNESS: Thickness of grid lines.
    """

    BOARD_SIZE: int = 8
    CELL_SIZE: int = 50
    BOARD_OFFSET: int = 50
    CHECKER_RADIUS: int = 20
    BACKGROUND_COLOR: Tuple[int, int, int] = (240, 240, 240)
    DARK_FIELD_COLOR: Tuple[int, int, int] = (0, 25, 80)
    LIGHT_FIELD_COLOR: Tuple[int, int, int] = (180, 225, 225)
    ORANGE_CHECKER_COLOR: Tuple[int, int, int] = (50, 85, 220)
    BLUE_CHECKER_COLOR: Tuple[int, int, int] = (205, 105, 60)
    GRID_COLOR: Tuple[int, int, int] = (0, 0, 0)
    GRID_THICKNESS: int = 3

    def __init__(
        self,
        colors: ColorConfig,
        consistency_threshold: int = 5,
        board_detector: Optional[BoardDetector] = None,
    ) -> None:
        """Initialize a new GameState instance.

        Args:
            colors: Configuration for game colors.
            consistency_threshold: Number of consistent states needed before accepting change.
            board_detector: Optional pre-configured board detector.
        """
        self.colors = colors
        self.consistency_threshold = consistency_threshold
        self._board_detector = board_detector or BoardDetector()
        self._current_state = self._get_default_initial_state()
        self._state_history: List[np.ndarray] = [self._current_state.copy()]
        self._last_detected_board: Optional[Board] = None
        self._cached_board_bg: Optional[np.ndarray] = None
        self._cached_checker_positions: Optional[Tuple[np.ndarray, np.ndarray]] = None

    @staticmethod
    def _get_default_initial_state() -> np.ndarray:
        """Create the initial game state with checkers in starting positions."""
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
            ],
            dtype=np.int32,
        )

    @staticmethod
    def _create_empty_state() -> np.ndarray:
        """Create an empty game state with no checkers."""
        return np.zeros((8, 8), dtype=np.int32)

    @classmethod
    def _build_state_from_checkers(
        cls, checkers: List[Checker], is_00_white: bool
    ) -> np.ndarray:
        """Build game state from detected checkers.

        Args:
            checkers: List of detected checkers.
            is_00_white: Whether the top-left field is white.

        Returns:
            Generated game state array.
        """
        state = cls._create_empty_state()
        for checker in checkers:
            state[checker.position[0], checker.position[1]] = (
                1 if checker.color == Color.ORANGE else -1
            )
        return np.rot90(state, 1) if not is_00_white else state

    def _try_update_state(self, new_state: np.ndarray) -> bool:
        """Update game state log and check for consistent changes.

        Args:
            new_state: New game state to check.

        Returns:
            True if game state was updated, False otherwise.
        """
        if any(not np.array_equal(log, new_state) for log in self._state_history):
            self._state_history = [new_state.copy()]
            return False

        if len(self._state_history) + 1 >= self.consistency_threshold:
            self._current_state = new_state.copy()
            self._state_history = [new_state.copy()]
            self._cached_checker_positions = None
            return True

        self._state_history.append(new_state.copy())
        return False

    def update(self, image: np.ndarray) -> Tuple[bool, np.ndarray]:
        """Update the game state based on the input image.

        Args:
            image: Source image from camera.

        Returns:
            Tuple of (whether state changed, current game state).
        """
        if image is None or not isinstance(image, np.ndarray) or image.size == 0:
            return False, self._current_state

        try:
            self._last_detected_board = self._board_detector.detect(image)
        except Exception:
            self._last_detected_board = None
            return False, self._current_state

        if self._last_detected_board is None or self._last_detected_board.frame is None:
            self._last_detected_board = None
            return False, self._current_state

        try:
            checkers = CheckerDetector.detect(
                self._last_detected_board,
                image,
                self.colors["orange"],
                self.colors["blue"],
            )
            new_state = self._build_state_from_checkers(
                checkers, self._last_detected_board.is_00_white(self.colors)
            )
            return self._try_update_state(new_state), self._current_state
        except Exception:
            return False, self._current_state

    def render_board(self) -> np.ndarray:
        """Generate visualization of current game state."""
        if self._cached_board_bg is None:
            self._cached_board_bg = self._render_board_background()

        img = self._cached_board_bg.copy()
        self._render_checkers(img)
        return img

    def get_last_detected_frame(self) -> np.ndarray:
        """Get the board image from the last update."""
        if self._last_detected_board is None or self._last_detected_board.frame is None:
            return np.array([], dtype=np.uint8)
        return self._last_detected_board.frame

    def _render_board_background(self) -> np.ndarray:
        """Create the checkered board background with grid."""
        img = np.full((500, 500, 3), self.BACKGROUND_COLOR, dtype=np.uint8)

        # Vectorized field drawing
        x_coords = np.arange(self.BOARD_SIZE)
        y_coords = np.arange(self.BOARD_SIZE)
        xx, yy = np.meshgrid(x_coords, y_coords)

        is_dark = (xx + yy) % 2 == 1
        dark_mask = is_dark.ravel()

        start_x = xx.ravel() * self.CELL_SIZE + self.BOARD_OFFSET
        start_y = yy.ravel() * self.CELL_SIZE + self.BOARD_OFFSET

        for i in range(len(start_x)):
            color = self.DARK_FIELD_COLOR if dark_mask[i] else self.LIGHT_FIELD_COLOR
            cv.rectangle(
                img,
                (start_x[i], start_y[i]),
                (start_x[i] + self.CELL_SIZE, start_y[i] + self.CELL_SIZE),
                color,
                -1,
            )

        # Draw grid lines
        offsets = np.arange(self.BOARD_SIZE + 1) * self.CELL_SIZE + self.BOARD_OFFSET
        for offset in offsets:
            cv.line(
                img,
                (offset, self.BOARD_OFFSET),
                (offset, 450),
                self.GRID_COLOR,
                self.GRID_THICKNESS,
            )
            cv.line(
                img,
                (self.BOARD_OFFSET, offset),
                (450, offset),
                self.GRID_COLOR,
                self.GRID_THICKNESS,
            )

        return img

    def _render_checkers(self, img: np.ndarray) -> None:
        """Draw checker pieces using precomputed positions."""
        if self._cached_checker_positions is None:
            self._update_checker_cache()

        if (
            self._cached_checker_positions is None
            or len(self._cached_checker_positions) == 0
        ):
            return

        centers, colors = self._cached_checker_positions
        for center, color in zip(centers, colors):
            cv.circle(
                img,
                (int(center[0]), int(center[1])),
                self.CHECKER_RADIUS,
                (int(color[0]), int(color[1]), int(color[2])),
                -1,
            )

    def _update_checker_cache(self) -> None:
        """Precompute checker positions and colors."""
        positions = np.argwhere(self._current_state != 0)
        if len(positions) == 0:
            self._cached_checker_positions = (np.array([]), np.array([]))
            return

        values = self._current_state[positions[:, 0], positions[:, 1]]
        centers = (
            positions * self.CELL_SIZE + self.BOARD_OFFSET + self.CELL_SIZE // 2
        )[:, [1, 0]]

        color_map = {
            1: self.ORANGE_CHECKER_COLOR,
            -1: self.BLUE_CHECKER_COLOR,
        }
        colors = np.array([color_map[v] for v in values])

        self._cached_checker_positions = (centers, colors)


if __name__ == "__main__":
    cap = cv.VideoCapture(0)
    game = GameState(
        {
            "orange": (250, 90, 20),
            "blue": (30, 85, 150),
            "black": (60, 50, 39),
            "white": (200, 200, 200),
        }
    )

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        try:
            updated, state = game.update(frame)
            cv.imshow("Game state", game.render_board())
            board_img = game.get_last_detected_frame()
            if board_img.size != 0:
                cv.imshow("Frame", board_img)
        except Exception as e:
            print(e)

        if cv.waitKey(30) == ord("q"):
            break

    cap.release()
    cv.destroyAllWindows()
