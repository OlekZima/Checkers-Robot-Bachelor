"""
Module for managing checkers game state and visualization.

This module provides functionality for managing a checkers game state,
including board visualization, game state updates, and state tracking.
"""

from typing import List, Optional, Tuple

import cv2
import numpy as np

from src.common.configs import ColorConfig, RecognitionConfig
from src.common.enums import Color
from .board_recognition.board import Board
from .checkers_recognition import Checkers


class GameState:
    """
    Manages the state and visualization of a checkers game.

    This class handles game state tracking, updates from computer vision input,
    and visualization of the current game state.

    Attributes:
        BOARD_SIZE: Size of the checkers board (8x8)
        CELL_SIZE: Pixel size of each board cell in visualization
        BOARD_OFFSET: Offset from the edge in visualization
        CHECKER_RADIUS: Radius of checker pieces in visualization
        BACKGROUND_COLOR: Background color in BGR format
        DARK_FIELD_COLOR: Color for dark fields in BGR format
        LIGHT_FIELD_COLOR: Color for light fields in BGR format
        ORANGE_CHECKER_COLOR: Color for orange checkers in BGR format
        BLUE_CHECKER_COLOR: Color for blue checkers in BGR format
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

    def __init__(
        self,
        colors: ColorConfig,
        lack_of_trust_level: int = 5,
        recognition_config: Optional[RecognitionConfig] = None,
    ) -> None:
        """
        Initialize a new Game instance.

        Args:
            colors: Configuration for game colors
            lack_of_trust_level: Number of consistent states needed before accepting change
            recognition_config: Configuration for computer vision recognition
        """
        self.colors = colors
        self.lack_of_trust_level = lack_of_trust_level
        self.recognition_config = recognition_config or RecognitionConfig()
        self.game_state = self._create_initial_game_state()
        self.game_state_log: List[np.ndarray] = [self.game_state]
        self.game_state_image: np.ndarray = np.array([])
        self._board: Board = None

    @staticmethod
    def _create_initial_game_state() -> np.ndarray:
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
            ]
        )

    @staticmethod
    def _create_empty_game_state() -> np.ndarray:
        """Create an empty game state with no checkers."""
        return np.zeros((8, 8), dtype=int)

    @classmethod
    def _build_game_state(cls, checkers: List[Checkers], is_00_white: bool) -> np.ndarray:
        """
        Build game state from detected checkers.

        Args:
            checkers: List of detected checkers
            is_00_white: Whether the top-left field is white

        Returns:
            numpy.ndarray: Generated game state
        """
        state = cls._create_empty_game_state()
        for checker in checkers:
            state[checker.pos[0]][checker.pos[1]] = 1 if checker.color == Color.ORANGE else -1
        return np.rot90(state, 1) if not is_00_white else state

    def _update_game_log(self, new_game_state: np.ndarray) -> bool:
        """
        Update game state log and check for consistent changes.

        Args:
            new_game_state: New game state to check

        Returns:
            bool: True if game state was updated, False otherwise
        """
        if any(not np.array_equal(log, new_game_state) for log in self.game_state_log):
            self.game_state_log = [new_game_state]
            return False

        if len(self.game_state_log) + 1 >= self.lack_of_trust_level:
            self.game_state = new_game_state
            self.game_state_log = [new_game_state]
            return True

        self.game_state_log.append(new_game_state)
        return False

    def update_game_state(self, image: np.ndarray) -> Tuple[bool, np.ndarray]:
        """
        Updates the game state based on the input image.
        Args:
            image (np.ndarray): source image from camera

        Returns:
            Tuple[bool, np.np.ndarray]: Tuple containing whether the game state changed and the game state itself
        """
        self._board = Board.detect_board(image.copy())
        checkers = Checkers.detect_checkers(
            self._board, image, self.colors["orange"], self.colors["blue"]
        )
        new_game_state = self._build_game_state(checkers, self._board.is_00_white(self.colors))
        self.game_state = new_game_state
        return self._update_game_log(new_game_state), self.game_state

    def get_game_state_image(self) -> np.ndarray:
        """Generate visualization of current game state."""
        img = self._create_board_background()
        self._draw_board_grid(img)
        self._draw_checkers(img)
        return img

    def get_board_image(self) -> np.ndarray:
        """Get the board image from the last update."""
        return self._board.get_frame_copy()

    def _create_board_background(self) -> np.ndarray:
        """Create the checkered board background."""
        img = np.zeros((500, 500, 3), np.uint8)
        img[:, :] = self.BACKGROUND_COLOR

        is_dark = False
        for x in range(self.BOARD_SIZE):
            for y in range(self.BOARD_SIZE):
                self._draw_board_field(img, x, y, is_dark)
                is_dark = not is_dark
            is_dark = not is_dark
        return img

    def _draw_board_field(self, img: np.ndarray, x: int, y: int, is_dark: bool) -> None:
        """Draw a single board field."""
        color = self.DARK_FIELD_COLOR if is_dark else self.LIGHT_FIELD_COLOR
        start_point = (
            x * self.CELL_SIZE + self.BOARD_OFFSET,
            y * self.CELL_SIZE + self.BOARD_OFFSET,
        )
        end_point = (start_point[0] + self.CELL_SIZE, start_point[1] + self.CELL_SIZE)
        cv2.rectangle(img, start_point, end_point, color, -1)

    def _draw_board_grid(self, img: np.ndarray) -> None:
        """Draw the board grid lines."""
        for i in range(self.BOARD_SIZE + 1):
            offset = i * self.CELL_SIZE + self.BOARD_OFFSET
            cv2.line(img, [offset, self.BOARD_OFFSET], [offset, 450], (0, 0, 0), 3)
            cv2.line(img, [self.BOARD_OFFSET, offset], [450, offset], (0, 0, 0), 3)

    def _draw_checkers(self, img: np.ndarray) -> None:
        """Draw checker pieces on the board."""
        for x, row in enumerate(self.game_state):
            for y, value in enumerate(row):
                if value != 0:
                    color = self.ORANGE_CHECKER_COLOR if value == 1 else self.BLUE_CHECKER_COLOR
                    center = (
                        x * self.CELL_SIZE + self.BOARD_OFFSET + self.CELL_SIZE // 2,
                        y * self.CELL_SIZE + self.BOARD_OFFSET + self.CELL_SIZE // 2,
                    )
                    cv2.circle(img, center, self.CHECKER_RADIUS, color, -1)


if __name__ == "__main__":
    camera_port = 2
    cap = cv2.VideoCapture(camera_port)
    game = GameState(
        ColorConfig(
            {
                "orange": (250, 90, 20),
                "blue": (30, 85, 150),
                "black": (60, 50, 39),
                "white": (200, 200, 200),
            }
        )
    )

    while True:
        ret, frame = cap.read()
        try:
            if game.update_game_state(frame):
                print("Game state changed")

            cv2.imshow("Game state", game.get_game_state_image())
            cv2.imshow("Frame", Board.detect_board(frame).frame)

        except Exception as e:
            print(e)
        if cv2.waitKey(30) == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
