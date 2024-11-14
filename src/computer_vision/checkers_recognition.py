import math
from enum import Enum
from src.checkers_game_and_decissions.utilities import get_avg_color, get_avg_pos


# def get_img_mask(pts, img_shape, margin=10):
#     center = get_avg_pos(pts)
#
#     for pt in pts:
#         dst = get_pts_dist(pt, center)
#         pt[0] = center[0] + int(float(pt[0] - center[0]) / dst * (dst + margin))
#         pt[1] = center[1] + int(float(pt[1] - center[1]) / dst * (dst + margin))
#
#     pts = np.array(pts)
#     mask = np.zeros(img_shape[:2], dtype="uint8")
#     cv.fillConvexPoly(mask, pts, 1)
#     return mask


def distance_from_color(bgr_sample, bgr_target):
    dist = (
            (bgr_sample[0] - bgr_target[0]) ** 2
            + (bgr_sample[1] - bgr_target[1]) ** 2
            + (bgr_sample[2] - bgr_target[2]) ** 2
    )
    dist = math.sqrt(dist)
    return dist


class Color(Enum):
    ORANGE = 1
    BLUE = 2


class Checkers:
    checkers = []  # storing all checkers

    def __init__(self, pos=None, color=Color.BLUE):
        if pos is None:
            pos = [0, 0]
        self.pos = pos
        self.color = color

    @classmethod
    def detect_checkers(cls, board, frame, bgr_red=None, bgr_green=None, color_dist_thresh=7):

        if bgr_green is None:
            bgr_green = [205, 110, 60]
        if bgr_red is None:
            bgr_red = [50, 80, 220]
        Checkers.checkers = []

        for x in range(0, len(board.points) - 1, 1):
            for y in range(0, len(board.points[x]) - 1, 1):
                board_tile_pts = [
                    board.points[x][y],
                    board.points[x][y + 1],
                    board.points[x + 1][y + 1],
                    board.points[x + 1][y],
                ]
                detected_checker_color = Checkers.detect_checker_color_if_present(
                    frame,
                    get_avg_pos(board_tile_pts),
                    bgr_red,
                    bgr_green,
                    color_dist_thresh,
                )
                if detected_checker_color is not None:
                    Checkers.checkers.append(
                        Checkers(pos=[x, y], color=detected_checker_color)
                    )

    @classmethod
    def detect_checker_color_if_present(cls, img, pt, bgr_red, bgr_green, color_dist_thresh, radius=2):
        test_sample = img[(pt[1] - radius): (pt[1] + radius), (pt[0] - radius): (pt[0] + radius)]
        bgr_sample_value = get_avg_color(test_sample)
        if distance_from_color(bgr_sample_value, bgr_red) <= color_dist_thresh:
            return Color.ORANGE
        if distance_from_color(bgr_sample_value, bgr_green) <= color_dist_thresh:
            return Color.BLUE
        return None
