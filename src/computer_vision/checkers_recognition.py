import math
from typing import Optional
from src.checkers_game_and_decissions.utilities import get_avg_color, get_avg_pos
from src.checkers_game_and_decissions.enum_entities import Color


class Checkers:
    def __init__(self, pos: Optional[list[int]] = None, color=Color.BLUE):
        self.pos = pos if pos is not None else [0, 0]
        self.color = color

    checkers = []
    bgr_blue = [205, 110, 60]
    bgr_orange = [50, 80, 220]
    color_dist_thresh = 7

    @classmethod
    def detect_checkers(cls, board, frame):
        cls.checkers = []

        for x in range(0, len(board.points) - 1, 1):
            for y in range(0, len(board.points[x]) - 1, 1):
                board_tile_pts = cls.get_board_tile_pts(board, x, y)
                detected_color = Checkers.detect_checker_color_if_present(
                    frame,
                    get_avg_pos(board_tile_pts),
                )
                if detected_color is not None:
                    cls.checkers.append(Checkers([x, y], detected_color))

    @staticmethod
    def get_board_tile_pts(board, x, y):
        return [
            board.points[x][y],
            board.points[x][y + 1],
            board.points[x + 1][y + 1],
            board.points[x + 1][y],
        ]

    @classmethod
    def detect_checker_color_if_present(cls, img, pt, radius=2) -> Optional[Color]:
        test_sample = img[
            (pt[1] - radius) : (pt[1] + radius), (pt[0] - radius) : (pt[0] + radius)
        ]
        bgr_sample = get_avg_color(test_sample)
        return cls.get_color_is_within_threshold(bgr_sample)

    @classmethod
    def get_color_is_within_threshold(cls, bgr_sample) -> Optional[Color]:
        if cls.distance_from_color(bgr_sample, cls.bgr_orange) <= cls.color_dist_thresh:
            return Color.ORANGE
        if cls.distance_from_color(bgr_sample, cls.bgr_blue) <= cls.color_dist_thresh:
            return Color.BLUE
        return None

    @staticmethod
    def distance_from_color(bgr_sample, bgr_target):
        distance = sum([(bgr_sample[i] - bgr_target[i]) ** 2 for i in range(3)])
        return math.sqrt(distance)
