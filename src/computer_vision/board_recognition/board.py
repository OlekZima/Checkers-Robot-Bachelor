"""Module for board detection and visualization."""

import math
from dataclasses import dataclass
import traceback
from typing import ClassVar, List, Optional, Tuple

import cv2
import numpy as np

from src.common.exceptions import (
    BoardDetectionError,
    InsufficientDataError,
    NoStartTileError,
)
from src.common.utilities import (
    HALF_PI,
    QUARTER_PI,
    TWO_PI,
    get_avg_pos,
    distance_from_color,
    get_avg_color,
    normalize_angle,
)

from .board_tile import BoardTile
from .contours_recognition import ContourProcessor


@dataclass
class BoardConfig:
    """Configuration for board visualization and detection."""

    vertex_color: Tuple[int, int, int] = (0, 255, 0)
    vertex_radius: int = 3
    line_color: Tuple[int, int, int] = (0, 255, 0)
    line_thickness: int = 1
    board_size: int = 9


class Board:
    contour_processor: ClassVar[ContourProcessor] = ContourProcessor()
    frame: Optional[np.ndarray] = None

    def __init__(self, iamge, board_tiles: Optional[List[BoardTile]] = None):
        self.frame = iamge
        Board.frame = iamge

        self.tiles = []

        if board_tiles is not None:
            self.tiles = board_tiles

        # shape == (9,9,2)
        self.points = [[None for _ in range(9)] for _ in range(9)]

        self.vertexes = [None, None, None, None]

        self._initialize_board()

    def _initialize_board(self) -> None:
        # STEP 0 - choosing a starting tile that has a neighbour in direction0
        start_tile = self._find_start_tile()

        # STEP 1 - finding indexes of start_tile by recursive function of BoardTile (flood_fill like)
        self._process_start_tile(start_tile)

        # STEP 2 - indexing all tiles by second recursive function
        # STEP 3 - assigning Board coordinates using indexes
        self._process_board_points(start_tile)
        self._draw_border_points()

        # STEP 5 - interpolating all points on board
        self.interpolate_borders()  # first I need to know all border points
        self.interpolate_inner_points()  # then I interpolate all inner points

        # STEP 6 - mirroring self.points for future use
        self.points = self.get_mirrored_2d_matrix_y_axis(self.points)

        # STEP 7 - drawing board
        self._draw_board()

    def _find_start_tile(self) -> BoardTile:
        start_tile = next((tile for tile in self.tiles if tile.neighbors_count == 4), 4)
        if start_tile is None:
            raise NoStartTileError("Couldn't find starting tile")
        return start_tile

    def _process_start_tile(self, start_tile: BoardTile) -> None:
        try:
            self.set_index_of_start_tile(start_tile)
            self._draw_tile_coordinates(start_tile)
        except InsufficientDataError as ide:
            raise ide
        except Exception as e:
            raise BoardDetectionError(
                "Error occured while trying to process start tile"
            ) from e

    @classmethod
    def _draw_tile_coordinates(cls, tile: BoardTile) -> None:
        cv2.putText(
            cls.frame,
            f"{tile.position[0]},{tile.position[1]}",
            tile.center,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

    def _process_board_points(self, start_tile: BoardTile) -> None:
        self.set_all_tiles_indexes(start_tile)

        dir_0 = start_tile.get_dir_0_radians()
        self.set_all_known_board_points(dir_0)
        self.calculate_vertexes()

    def _draw_board(self):
        for i in range(0, 9):
            for j in range(0, 9):
                if i != 8:
                    if (
                        self.points[i][j] is not None
                        and self.points[i + 1][j] is not None
                    ):
                        cv2.line(
                            self.frame,
                            self.points[i][j],
                            self.points[i + 1][j],
                            (0, 255, 0),
                            1,
                        )
                if j != 8:
                    if (
                        self.points[i][j] is not None
                        and self.points[i][j + 1] is not None
                    ):
                        cv2.line(
                            self.frame,
                            self.points[i][j],
                            self.points[i][j + 1],
                            (0, 255, 0),
                            1,
                        )

    def _draw_border_points(self):
        cv2.circle(self.frame, self.vertexes[0], 3, (0, 255, 0), -1)
        cv2.circle(self.frame, self.vertexes[1], 3, (0, 255, 0), -1)
        cv2.circle(self.frame, self.vertexes[2], 3, (0, 255, 0), -1)
        cv2.circle(self.frame, self.vertexes[3], 3, (0, 255, 0), -1)

    @classmethod
    def detect_board(cls, img_src):
        try:
            contours = cls.contour_processor.get_contours(img_src)
            BoardTile.create_tiles(img_src, contours)
            return Board(img_src, BoardTile.tiles)
        except BoardDetectionError as bde:
            raise bde
        except InsufficientDataError as ide:
            raise ide
        except Exception as e:
            raise BoardDetectionError(
                "Unknown Error occured while trying to detect board"
            ) from e

    @classmethod
    def _calculate_directions(cls, start_tile: BoardTile) -> Dict[str, float]:
        base_direction = start_tile.get_dir_0_radians()
        return {
            "dir_0": base_direction,
            "dir_01": normalize_angle(base_direction + QUARTER_PI),
            "dir_1": normalize_angle(base_direction + HALF_PI),
            "dir_12": normalize_angle(base_direction + HALF_PI + QUARTER_PI),
            "dir_2": normalize_angle(base_direction + math.pi),
            "dir_23": normalize_angle(base_direction + math.pi + QUARTER_PI),
            "dir_3": normalize_angle(base_direction + math.pi + HALF_PI),
            "dir_30": normalize_angle(base_direction + math.pi + HALF_PI + QUARTER_PI),
        }

    @classmethod
    def set_index_of_start_tile(cls, start_tile: BoardTile) -> None:
        # Calculate base direction and derived directions
        directions = cls._calculate_directions(start_tile)

        # Calculate X index
        dir_1_steps = cls._get_steps_in_direction(
            start_tile,
            directions["dir_01"],
            directions["dir_12"],
            directions["dir_1"],
            1,
        )
        dir_3_steps = cls._get_steps_in_direction(
            start_tile,
            directions["dir_23"],
            directions["dir_30"],
            directions["dir_3"],
            3,
        )

        if dir_1_steps + dir_3_steps != 7:
            raise InsufficientDataError(
                "Not enough board is recognized on the `X` axis"
            )
        start_tile.set_x_index(dir_3_steps)

        # Calculate Y index
        dir_2_steps = cls._get_steps_in_direction(
            start_tile,
            directions["dir_12"],
            directions["dir_23"],
            directions["dir_2"],
            2,
        )
        dir_0_steps = cls._get_steps_in_direction(
            start_tile,
            directions["dir_30"],
            directions["dir_01"],
            directions["dir_0"],
            0,
        )

        if dir_2_steps + dir_0_steps != 7:
            raise InsufficientDataError(
                "Not enough board is recognized on the `Y` axis"
            )
        start_tile.set_y_index(dir_0_steps)

    @staticmethod
    def _get_steps_in_direction(
        tile: BoardTile, start_rad: float, end_rad: float, dir_rad: float, dir_idx: int
    ) -> int:
        neighbor = tile.get_neighbor_in_rad_range(start_rad, end_rad)
        if neighbor is None:
            return 0
        return tile.get_num_of_steps_in_dir_rad(dir_rad, dir_idx)

    @classmethod
    def set_all_tiles_indexes(cls, start_tile: BoardTile):
        dir_0 = start_tile.get_dir_0_radians()
        start_tile.index_neighbors(dir_0)

    def set_all_known_board_points(self, dir_0):
        dir_1 = dir_0 + HALF_PI
        if dir_1 >= TWO_PI:
            dir_1 -= TWO_PI
        dir_2 = dir_1 + HALF_PI
        if dir_2 >= TWO_PI:
            dir_2 -= TWO_PI
        dir_3 = dir_2 + HALF_PI
        if dir_3 >= TWO_PI:
            dir_3 -= TWO_PI

        for tile in self.tiles:
            if tile.position[0] is None or tile.position[1] is None:
                continue
            if self.points[tile.position[0]][tile.position[1]] is None:
                self.points[tile.position[0]][tile.position[1]] = (
                    tile.get_vertex_in_rad_range(dir_3, dir_0)
                )
            if self.points[tile.position[0] + 1][tile.position[1]] is None:
                self.points[tile.position[0] + 1][tile.position[1]] = (
                    tile.get_vertex_in_rad_range(dir_0, dir_1)
                )
            if self.points[tile.position[0] + 1][tile.position[1] + 1] is None:
                self.points[tile.position[0] + 1][tile.position[1] + 1] = (
                    tile.get_vertex_in_rad_range(dir_1, dir_2)
                )
            if self.points[tile.position[0]][tile.position[1] + 1] is None:
                self.points[tile.position[0]][tile.position[1] + 1] = (
                    tile.get_vertex_in_rad_range(dir_2, dir_3)
                )

    @classmethod
    def extrapolate_last_point(
        cls,
        points=[[0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
    ):
        # This function will take one side of a Board as list of points
        # Then check what are 2 not None values the most appart from itself
        # Finally extrapolating the last item on this list accordingly

        min_idx = 8
        max_idx = 0
        for i, p in enumerate(points):
            if p is not None:
                if i < min_idx:
                    min_idx = i
                if i > max_idx:
                    max_idx = i

        vector_init_len = max_idx - min_idx
        vector_final_len = 8 - min_idx
        vector = [
            points[max_idx][0] - points[min_idx][0],
            points[max_idx][1] - points[min_idx][1],
        ]
        vector = [
            int(float(v) / float(vector_init_len) * vector_final_len) for v in vector
        ]
        res = [points[min_idx][0] + vector[0], points[min_idx][1] + vector[1]]
        return res

    def calculate_vertexes(self) -> None:
        if self.points[0][0] is not None:
            self.vertexes[0] = self.points[0][0]
        if self.points[8][0] is not None:
            self.vertexes[1] = self.points[8][0]
        if self.points[8][8] is not None:
            self.vertexes[2] = self.points[8][8]
        if self.points[0][8] is not None:
            self.vertexes[3] = self.points[0][8]

        if self.vertexes[0] is None:
            P_01 = [v[0] for v in self.points]
            P_10 = P_01[::-1]
            pred1 = Board.extrapolate_last_point(points=P_10)
            P_03 = self.points[0]
            P_30 = P_03[::-1]
            pred2 = Board.extrapolate_last_point(points=P_30)
            res = get_avg_pos([pred1, pred2])
            self.vertexes[0] = res
            self.points[0][0] = res
        if self.vertexes[1] is None:
            P_01 = [v[0] for v in self.points]
            pred1 = Board.extrapolate_last_point(points=P_01)
            P_12 = self.points[8]
            P_21 = P_12[::-1]
            pred2 = Board.extrapolate_last_point(points=P_21)
            res = get_avg_pos([pred1, pred2])
            self.vertexes[1] = res
            self.points[8][0] = res

        if self.vertexes[2] is None:
            P_12 = self.points[8]
            pred1 = Board.extrapolate_last_point(points=P_12)
            P_32 = [v[8] for v in self.points]
            pred2 = Board.extrapolate_last_point(points=P_32)
            res = get_avg_pos([pred1, pred2])
            self.vertexes[2] = res
            self.points[8][8] = res

        if self.vertexes[3] is None:
            P_32 = [v[8] for v in self.points]
            P_23 = P_32[::-1]
            pred1 = Board.extrapolate_last_point(points=P_23)
            P_03 = self.points[0]
            pred2 = Board.extrapolate_last_point(points=P_03)
            res = get_avg_pos([pred1, pred2])
            self.vertexes[3] = res
            self.points[0][8] = res

    def interpolate_borders(self) -> None:

        P_01 = [v[0] for v in self.points]
        P_12 = self.points[8]
        P_32 = [v[8] for v in self.points]
        P_03 = self.points[0]
        # Border 01
        for i in range(1, len(P_01) - 1, 1):
            if P_01[i] is None:
                pts_to_avg = []
                for j in range(i + 1, len(P_01), 1):
                    pts_to_avg.append(P_01[i - 1])
                    if P_01[j] is not None:
                        pts_to_avg.append(P_01[j])
                        break

                extrapolation_pts = self.points[i][::-1]
                extrapolation_val = Board.extrapolate_last_point(
                    points=extrapolation_pts
                )
                pts_to_avg = [get_avg_pos(pts_to_avg), extrapolation_val]
                self.points[i][0] = get_avg_pos(pts_to_avg)
                P_01[i] = self.points[i][0]
        # Border 12
        for i in range(1, len(P_12) - 1, 1):
            if P_12[i] is None:
                pts_to_avg = []
                for j in range(i + 1, len(P_12), 1):
                    pts_to_avg.append(P_12[i - 1])
                    if P_12[j] is not None:
                        pts_to_avg.append(P_12[j])
                        break

                extrapolation_pts = [l[i] for l in self.points]
                extrapolation_val = Board.extrapolate_last_point(
                    points=extrapolation_pts
                )
                pts_to_avg = [get_avg_pos(pts_to_avg), extrapolation_val]
                self.points[8][i] = get_avg_pos(pts_to_avg)
                P_12[i] = self.points[8][i]
        # Border 23
        for i in range(1, len(P_32) - 1, 1):
            if P_32[i] is None:
                pts_to_avg = []
                for j in range(i + 1, len(P_32), 1):
                    pts_to_avg.append(P_32[i - 1])
                    if P_32[j] is not None:
                        pts_to_avg.append(P_32[j])
                        break

                extrapolation_pts = self.points[i]
                extrapolation_val = Board.extrapolate_last_point(
                    points=extrapolation_pts
                )
                pts_to_avg = [get_avg_pos(pts_to_avg), extrapolation_val]
                self.points[i][8] = get_avg_pos(pts_to_avg)
                P_32[i] = self.points[i][8]
        # Border 30
        for i in range(1, len(P_03) - 1, 1):
            if P_03[i] is None:
                pts_to_avg = []
                for j in range(i + 1, len(P_03), 1):
                    pts_to_avg.append(P_03[i - 1])
                    if P_03[j] is not None:
                        pts_to_avg.append(P_03[j])
                        break

                extrapolation_pts = [l[i] for l in self.points][::-1]
                extrapolation_val = Board.extrapolate_last_point(
                    points=extrapolation_pts
                )
                pts_to_avg = [get_avg_pos(pts_to_avg), extrapolation_val]
                self.points[0][i] = get_avg_pos(pts_to_avg)
                P_03[i] = self.points[0][i]

    def interpolate_inner_points(self) -> None:
        for i in range(1, len(self.points) - 1, 1):
            for j in range(1, len(self.points[i]) - 1, 1):
                if self.points[i][j] is None:
                    pts_to_avg_same_i = []
                    pts_to_avg_same_j = []
                    for k in range(j + 1, len(self.points[i]), 1):
                        pts_to_avg_same_i.append(self.points[i][j - 1])
                        if self.points[i][k] is not None:
                            pts_to_avg_same_i.append(self.points[i][k])
                            break
                    for k in range(i + 1, len(self.points), 1):
                        pts_to_avg_same_j.append(self.points[i - 1][j])
                        if self.points[k][j] is not None:
                            pts_to_avg_same_j.append(self.points[k][j])
                            break
                    self.points[i][j] = get_avg_pos(
                        [get_avg_pos(pts_to_avg_same_i), get_avg_pos(pts_to_avg_same_j)]
                    )

    def is_point_in_field(self, x, y, pt=[0, 0]) -> bool:
        # the idea is to check if field area == area of 4 triangles with pt vertex
        v1 = self.points[x][y]
        v2 = self.points[x + 1][y]
        v3 = self.points[x + 1][y + 1]
        v4 = self.points[x][y + 1]
        field_area = self.get_triangle_area(v1, v2, v3) + self.get_triangle_area(
            v3, v4, v1
        )
        calculated_area = (
            self.get_triangle_area(v1, pt, v2)
            + self.get_triangle_area(v2, pt, v3)
            + self.get_triangle_area(v3, pt, v4)
            + self.get_triangle_area(v4, pt, v1)
        )
        if field_area == calculated_area:
            return True
        return False

    def is_00_white(
        self,
        radius=4,
        dark_field_bgr=[0, 0, 0],
        light_field_bgr=[255, 255, 255],
        red_bgr=[0, 0, 255],
        green_bgr=[0, 255, 0],
        color_dist_thresh=60,
    ) -> bool:
        pt = get_avg_pos(
            [self.points[0][0], self.points[0][1], self.points[1][1], self.points[1][0]]
        )
        sample = self.frame[
            (pt[1] - radius) : (pt[1] + radius), (pt[0] - radius) : (pt[0] + radius)
        ]
        sample_avg_bgr = get_avg_color(sample)
        if (
            distance_from_color(sample_avg_bgr, dark_field_bgr)
            < distance_from_color(sample_avg_bgr, light_field_bgr)
            or distance_from_color(sample_avg_bgr, red_bgr) <= color_dist_thresh
            or distance_from_color(sample_avg_bgr, green_bgr) <= color_dist_thresh
        ):
            return False
        else:
            return True

    @staticmethod
    def get_mirrored_2d_matrix_y_axis(matrix):
        new_matrix = []
        col_num = len(matrix)
        for c in range(0, col_num, 1):
            new_matrix.append(matrix[col_num - 1 - c])
        return new_matrix

    @staticmethod
    def get_triangle_area(p1=[0, 0], p2=[0, 0], p3=[0, 0]):
        # Area = (1/2) |x1(y2 − y3) + x2(y3 − y1) + x3(y1 − y2)|
        area = abs(
            p1[0] * (p2[1] - p3[1]) + p2[0] * (p3[1] - p1[1]) + p3[0] * (p1[1] - p2[1])
        )
        area = float(area) / 2.0
        return area

    @classmethod
    def get_frame_copy(cls):
        return cls.frame.copy()


if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    processor = ContourProcessor()
    while True:
        _, img = cap.read()

        try:
            board = Board.detect_board(img)
        except Exception as e:
            print(traceback.format_exc())

        print(len(BoardTile.tiles))
        draw_image = Board.get_frame_copy()
        cv2.imshow("RESULT", draw_image)
        if cv2.waitKey(0) == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
