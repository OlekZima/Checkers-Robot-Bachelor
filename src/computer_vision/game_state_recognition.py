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
    DARK_FIELD_COLOR: Tuple[int, int, int] = (80, 80, 80)
    LIGHT_FIELD_COLOR: Tuple[int, int, int] = (230, 230, 230)
    ORANGE_CHECKER_COLOR: Tuple[int, int, int] = (50, 85, 220)
    BLUE_CHECKER_COLOR: Tuple[int, int, int] = (255, 160, 0)
    GRID_COLOR: Tuple[int, int, int] = (60, 60, 60)
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
        self._candidate_state: Optional[np.ndarray] = None
        self._candidate_count: int = 0
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
        if self._candidate_state is None or not np.array_equal(
            new_state, self._candidate_state
        ):
            self._candidate_state = new_state.copy()
            self._candidate_count = 1
            if self.consistency_threshold <= 1:
                self._current_state = new_state.copy()
                self._candidate_state = None
                self._candidate_count = 0
                self._cached_checker_positions = None
                return True
            return False

        self._candidate_count += 1
        if self._candidate_count >= self.consistency_threshold:
            self._current_state = new_state.copy()
            self._candidate_state = None
            self._candidate_count = 0
            self._cached_checker_positions = None
            return True

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

        # Dark squares should start at the top-left for standard checkerboard coloring
        is_dark = (xx + yy) % 2 == 0
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
            cv.circle(
                img,
                (int(center[0]), int(center[1])),
                self.CHECKER_RADIUS,
                (255, 255, 255),
                2,
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

    def debug_sample_tiles(self) -> None:
        """Debug method: sample colors from a few tiles and show threshold filtering."""
        if self._last_detected_board is None:
            print("  [DEBUG] No board detected yet")
            return
        
        from src.common.configs import RecognitionConfig
        from src.common.utils import convert_bgr_to_hsv, hue_diff
        
        config = RecognitionConfig()
        board = self._last_detected_board
        
        # Get a few tile centers
        centers, positions = CheckerDetector._extract_tile_centers(board)
        if len(centers) < 5:
            print("  [DEBUG] Not enough tiles detected")
            return
        
        # Sample first 5 tiles
        sample_indices = [0, 1, 2, 3, 4]
        sampled_colors = CheckerDetector._sample_region_colors(board.frame, centers[sample_indices], radius=config.radius)
        sampled_hsv = CheckerDetector._convert_bgr_array_to_hsv(sampled_colors)
        
        # Reference colors
        orange_hsv = CheckerDetector._convert_bgr_to_hsv(self.colors["orange"])
        blue_hsv = CheckerDetector._convert_bgr_to_hsv(self.colors["blue"])
        
        print(f"  [DEBUG] Reference colors - Orange HSV: {orange_hsv}, Blue HSV: {blue_hsv}")
        print(f"  [DEBUG] Thresholds: hue_tol={config.hsv_hue_tolerance}, sat_min={config.hsv_sat_min}, val_min={config.hsv_val_min}")
        
        # Extract sample positions (positions is a list, not numpy array)
        sample_positions = [positions[i] for i in sample_indices]
        for idx, (pos, hsv) in enumerate(zip(sample_positions, sampled_hsv)):
            h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])
            sat_ok = "✓" if s >= config.hsv_sat_min else "✗"
            val_ok = "✓" if v >= config.hsv_val_min else "✗"
            orange_hue_diff = hue_diff(h, orange_hsv[0])
            blue_hue_diff = hue_diff(h, blue_hsv[0])
            hue_match = "O" if orange_hue_diff <= config.hsv_hue_tolerance else ("B" if blue_hue_diff <= config.hsv_hue_tolerance else "-")
            print(f"    Tile {pos}: HSV({h:3d}, {s:3d}, {v:3d}) | S:{sat_ok} V:{val_ok} | Hue: O{orange_hue_diff:2d} B{blue_hue_diff:2d} Match:{hue_match}")


if __name__ == "__main__":
    cap = cv.VideoCapture(0)
    color_config: ColorConfig = {
        "orange": (40, 90, 245),
        "blue": (180, 112, 85),
        "black": (45, 45, 45),
        "white": (200, 200, 200),
    }

    # Use low consistency_threshold for testing
    game = GameState(
        color_config,
        consistency_threshold=1,  # Update immediately for testing
    )

    frame_count = 0
    prev_checker_positions = set()
    board_detection_failures = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        try:
            updated, state = game.update(frame)
            
            board_detected = game._last_detected_board is not None
            if not board_detected:
                board_detection_failures += 1

            detected_checkers: List[Checker] = []
            detected_state = game._create_empty_state()
            if board_detected:
                try:
                    detected_checkers = CheckerDetector.detect(
                        game._last_detected_board,
                        frame,
                        game.colors["orange"],
                        game.colors["blue"],
                    )
                    detected_state = game._build_state_from_checkers(
                        detected_checkers,
                        game._last_detected_board.is_00_white(game.colors),
                    )
                except Exception as inner_e:
                    print(f"[Frame {frame_count}] DEBUG: checker detection error: {type(inner_e).__name__}: {inner_e}")

            detected_data = [
                (x, y, detected_state[x, y])
                for x in range(8)
                for y in range(8)
                if detected_state[x, y] != 0
            ]
            curr_checker_positions = set(detected_data)
            checkers_changed = curr_checker_positions != prev_checker_positions

            state_status = "✓ STATE UPDATED" if updated else "○ State unchanged"
            candidate_count = game._candidate_count
            consistency_pct = (candidate_count / max(1, game.consistency_threshold)) * 100
            board_status = "✓ Board detected" if board_detected else "✗ No board detected"

            if frame_count % 3 == 0:
                print(
                    f"[Frame {frame_count:3d}] {board_status} | Detected: {len(detected_checkers)} | {state_status} | Consistency: {candidate_count}/{game.consistency_threshold} ({consistency_pct:.0f}%)"
                )
                if checkers_changed:
                    print("       → Detected checker configuration changed!")
                    for x, y, val in sorted(detected_data):
                        color_name = "ORANGE" if val > 0 else "BLUE"
                        print(f"         • {color_name} at ({x}, {y})")

            if updated:
                print(f"       ✓✓✓ STATE UPDATED! Non-zero cells: {np.count_nonzero(state)}")
                print(f"           Updated state: {state}")
                print(f"           Detected state: {detected_state}")

            if frame_count % 30 == 0:
                if board_detected:
                    print("       [Sampling tile colors]")
                    game.debug_sample_tiles()
                else:
                    print("       [Skipping tile debug - board not detected]")

            prev_checker_positions = curr_checker_positions

            cv.imshow("Game state", game.render_board())
            board_img = game.get_last_detected_frame()
            if board_img.size != 0:
                cv.imshow("Detected board", board_img)
        except Exception as e:
            print(f"[Frame {frame_count}] ERROR: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()

        if cv.waitKey(30) == ord("q"):
            break

    cap.release()
    cv.destroyAllWindows()
    
    # Print summary statistics
    if frame_count > 0:
        detection_rate = ((frame_count - board_detection_failures) / frame_count) * 100
        print(f"\n═══ Test Summary ═══")
        print(f"Total frames processed: {frame_count}")
        print(f"Board detection failures: {board_detection_failures}")
        print(f"Board detection success rate: {detection_rate:.1f}%")
        print(f"Current game state:\n{game._current_state}")
