from typing import List, Optional, Tuple

from src.common.configs import RecognitionConfig
from src.common.enums import Color
from src.common.utils import distance_from_color, get_avg_color, get_avg_pos

from .board_recognition.board import Board


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
    ) -> List["Checkers"]:
        """Detect checkers on the board using RGB colors."""
        if color_dist_thresh is None:
            color_dist_thresh = RecognitionConfig.color_dist_threshold

        # Convert RGB to BGR for OpenCV
        orange_bgr = cls._rgb_to_bgr(orange_rgb)
        blue_bgr = cls._rgb_to_bgr(blue_rgb)

        checkers: List[Checkers] = []
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
                    checkers.append(cls(detected_color, (x, y)))

        return checkers

    @staticmethod
    def _rgb_to_bgr(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Convert RGB color to BGR color."""
        b, g, r = rgb[::-1]
        return b, g, r

    @staticmethod
    def _get_board_tile_pts(board: Board, x: int, y: int) -> List[tuple[int, int]]:
        """Get the four corner points of a board tile."""
        pts = [
            board.points[x][y],
            board.points[x][y + 1],
            board.points[x + 1][y + 1],
            board.points[x + 1][y],
        ]
        return [pt for pt in pts if pt is not None]

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
        height, width = img.shape[:2]
        x_min = max(0, pt[0] - radius)
        x_max = min(width, pt[0] + radius)
        y_min = max(0, pt[1] - radius)
        y_max = min(height, pt[1] + radius)

        if x_min >= x_max or y_min >= y_max:
            return None

        test_sample = img[y_min:y_max, x_min:x_max]
        if test_sample.size == 0:
            return None

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
