from typing import Optional, Self
from src.checkers_game_and_decisions.utilities import (
    get_avg_color,
    get_avg_pos,
    distance_from_color,
)
from src.checkers_game_and_decisions.enum_entities import Color


class Checkers:
    checkers: list[Self] = []
    bgr_blue: list[int] = [205, 110, 60]
    bgr_orange: list[int] = [50, 80, 220]
    color_dist_thresh: int = 7

    def __init__(self, color: Color, pos=None):
        if pos is None:
            pos = [0, 0]

        self.pos = pos
        self.color = color

    @classmethod
    def detect_checkers(
        cls,
        board,
        frame,
        orange_bgr: Optional[list[int]] = None,
        blue_bgr: Optional[list[int]] = None,
        color_dist_thresh: Optional[int] = None,
    ):

        if orange_bgr is None:
            orange_bgr = cls.bgr_orange
        if blue_bgr is None:
            blue_bgr = cls.bgr_blue
        if color_dist_thresh is None:
            color_dist_thresh = cls.color_dist_thresh

        cls.checkers = []

        for x in range(len(board.points) - 1):
            for y in range(len(board.points[x]) - 1):
                board_tile_pts = cls._get_board_tile_pts(board, x, y)
                detected_color = Checkers._detect_checker_color_if_present(
                    frame,
                    get_avg_pos(board_tile_pts),
                )
                if detected_color is not None:
                    cls.checkers.append(Checkers(detected_color, (x, y)))

    @staticmethod
    def _get_board_tile_pts(board, x, y):
        return [
            board.points[x][y],
            board.points[x][y + 1],
            board.points[x + 1][y + 1],
            board.points[x + 1][y],
        ]

    @classmethod
    def _detect_checker_color_if_present(cls, img, pt, radius=2) -> Optional[Color]:
        test_sample = img[
            (pt[1] - radius) : (pt[1] + radius), (pt[0] - radius) : (pt[0] + radius)
        ]
        bgr_sample = get_avg_color(test_sample)
        return cls._get_color_is_within_threshold(bgr_sample)

    @classmethod
    def _get_color_is_within_threshold(cls, bgr_sample) -> Optional[Color]:
        if distance_from_color(bgr_sample, cls.bgr_orange) <= cls.color_dist_thresh:
            return Color.ORANGE
        if distance_from_color(bgr_sample, cls.bgr_blue) <= cls.color_dist_thresh:
            return Color.BLUE
        return None
