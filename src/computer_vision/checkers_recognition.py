from typing import List, Optional, Self, Tuple
from src.common.enums import Color
from src.common.utils import distance_from_color, get_avg_color, get_avg_pos
from src.computer_vision.board_recognition.board import Board
from src.common.dataclasses import RecognitionConfig


class Checkers:
    """Class representing checkers and their detection on the board."""

    def __init__(self, color: Color, pos: Tuple[int, int] = (0, 0)):
        self.pos = pos
        self.color = color

    def __repr__(self) -> str:
        return f"Checker({self.color.name}, {self.pos})"

    @classmethod
    def detect_checkers(
        cls,
        board: Board,
        frame,
        orange_rgb: Tuple[int, int, int],
        blue_rgb: Tuple[int, int, int],
        color_dist_thresh: Optional[int] = None,
    ) -> List[Self]:
        """Detect checkers on the board using RGB colors."""
        if color_dist_thresh is None:
            color_dist_thresh = RecognitionConfig.color_dist_threshold

        # Convert RGB to BGR for OpenCV
        orange_bgr = cls._rgb_to_bgr(orange_rgb)
        blue_bgr = cls._rgb_to_bgr(blue_rgb)

        checkers: List[Self] = []
        for x in range(len(board.points) - 1):
            for y in range(len(board.points[x]) - 1):
                board_tile_pts = cls._get_board_tile_pts(board, x, y)
                detected_color = cls._detect_checker_color_if_present(
                    frame,
                    get_avg_pos(board_tile_pts),
                    orange_bgr,
                    blue_bgr,
                    color_dist_thresh,
                )
                if detected_color is not None:
                    checkers.append(Checkers(detected_color, (x, y)))

        return checkers

    @staticmethod
    def _rgb_to_bgr(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Convert RGB color to BGR color."""
        return rgb[::-1]

    @staticmethod
    def _get_board_tile_pts(board: Board, x: int, y: int) -> List[Tuple[int, int]]:
        """Get the four corner points of a board tile."""
        return [
            board.points[x][y],
            board.points[x][y + 1],
            board.points[x + 1][y + 1],
            board.points[x + 1][y],
        ]

    @classmethod
    def _detect_checker_color_if_present(
        cls,
        img,
        pt: Tuple[int, int],
        bgr_orange: Tuple[int, int, int],
        bgr_blue: Tuple[int, int, int],
        color_dist_thresh: int,
        radius: int = 2,
    ) -> Optional[Color]:
        """Detect checker color at given point if present."""
        test_sample = img[(pt[1] - radius) : (pt[1] + radius), (pt[0] - radius) : (pt[0] + radius)]
        bgr_sample = get_avg_color(test_sample)
        return cls._get_color_if_within_threshold(
            bgr_sample, bgr_orange, bgr_blue, color_dist_thresh
        )

    @staticmethod
    def _get_color_if_within_threshold(
        bgr_sample: Tuple[int, int, int],
        bgr_orange: Tuple[int, int, int],
        bgr_blue: Tuple[int, int, int],
        color_dist_thresh: int,
    ) -> Optional[Color]:
        """Determine checker color based on color distance threshold."""
        if distance_from_color(bgr_sample, bgr_orange) <= color_dist_thresh:
            return Color.ORANGE
        if distance_from_color(bgr_sample, bgr_blue) <= color_dist_thresh:
            return Color.BLUE
        return None
