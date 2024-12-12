"""Module for board detection and visualization."""

import math
from dataclasses import dataclass
import traceback
from typing import ClassVar, Dict, List, Optional, Self, Tuple

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
    get_avg_pos,
    distance_from_color,
    get_avg_color,
    normalize_angle,
)

from .board_tile import BoardTile
from .contours_recognition import ContourProcessor


class Board:



    contour_processor: ClassVar[ContourProcessor] = ContourProcessor()
    frame: ClassVar[np.ndarray] = np.array([])
    _instance: ClassVar[Optional["Board"]] = None

    def __init__(self) -> None:
        self.tiles: List[BoardTile] = []
        self.points: List[List[Optional[List[int]]]] = [
            [None for _ in range(9)] for _ in range(9)
        ]
        self.vertexes: List[Optional[List[int]]] = [None] * 4

    @classmethod
    def detect_board(cls, image: np.ndarray) -> "Board":



        try:
            # Create instance if it doesn't exist
            if cls._instance is None:
                cls._instance = cls()

            # Update frame
            cls.frame = image

            # Reset board state
            cls._instance._reset_state()  # pylint: disable=protected-access

            # Process board
            contours = cls.contour_processor.get_contours(image)
            BoardTile.create_tiles(image, contours)
            cls._instance.tiles = BoardTile.tiles

            # Initialize board
            cls._instance._initialize_board()  # pylint: disable=protected-access

            return cls._instance

        except (BoardDetectionError, InsufficientDataError) as e:
            raise e
        except Exception as e:
            raise BoardDetectionError(
                "Unknown Error occurred while trying to detect board"
            ) from e

    def _reset_state(self) -> None:
        self.tiles = []
        self.points = [[None for _ in range(9)] for _ in range(9)]
        self.vertexes = [None] * 4

    @classmethod
    def get_frame_copy(cls):
        return cls.frame.copy()

    def _initialize_board(self) -> None:
        # STEP 0 - choosing a starting tile that has a neighbour in direction0
        start_tile = self._find_start_tile()

        # STEP 1 - finding indexes of start_tile by recursive function of BoardTile
        self._process_start_tile(start_tile)

        # STEP 2 - indexing all tiles by second recursive function
        # STEP 3 - assigning Board coordinates using indexes
        self._process_board_points(start_tile)
        self._draw_border_points()

        # STEP 5 - interpolating all points on board
        self._interpolate_borders()  # first I need to know all border points
        self._interpolate_inner_points()  # then I interpolate all inner points

        # STEP 6 - mirroring self.points for future use
        self.points = self._get_mirrored_2d_matrix_y_axis(self.points)

        # STEP 7 - drawing board
        self._draw_board()

    def _find_start_tile(self) -> BoardTile:
        start_tile = next((tile for tile in self.tiles if tile.neighbors_count == 4), 4)
        if start_tile is None:
            raise NoStartTileError("Couldn't find starting tile")
        return start_tile

    def _process_start_tile(self, start_tile: BoardTile) -> None:
        try:
            self._set_index_of_start_tile(start_tile)
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
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    def _process_board_points(self, start_tile: BoardTile) -> None:
        self._set_all_tiles_indexes(start_tile)

        dir_0 = start_tile.get_dir_0_radians()
        self._set_all_known_board_points(dir_0)
        self._calculate_vertexes()

    def _draw_board(self) -> None:
        for i in range(0, 9):
            for j in range(0, 9):
                if i != 8:
                    if (
                        self.points[i][j] is not None
                        and self.points[i + 1][j] is not None
                    ):
                        cv2.line(
                            Board.frame,
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
                            Board.frame,
                            self.points[i][j],
                            self.points[i][j + 1],
                            (0, 255, 0),
                            1,
                        )

    def _draw_border_points(self) -> None:
        cv2.circle(Board.frame, self.vertexes[0], 3, (0, 255, 0), -1)
        cv2.circle(Board.frame, self.vertexes[1], 3, (0, 255, 0), -1)
        cv2.circle(Board.frame, self.vertexes[2], 3, (0, 255, 0), -1)
        cv2.circle(Board.frame, self.vertexes[3], 3, (0, 255, 0), -1)

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
    def _set_index_of_start_tile(cls, start_tile: BoardTile) -> None:
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
    def _set_all_tiles_indexes(cls, start_tile: BoardTile):
        dir_0 = start_tile.get_dir_0_radians()
        start_tile.index_neighbors(dir_0)

    def _set_all_known_board_points(self, dir_0: float) -> None:
        directions = self._calculate_orthogonal_directions(dir_0)
        vertex_positions = self._get_vertex_positions()

        for tile in self.tiles:
            if not self._is_valid_tile_position(tile):
                continue

            for pos, dir_range in vertex_positions:
                x = tile.position[0] + pos[0]
                y = tile.position[1] + pos[1]

                if self.points[x][y] is None:
                    start_dir, end_dir = [directions[i] for i in dir_range]
                    self.points[x][y] = tile.get_vertex_in_rad_range(start_dir, end_dir)

    def _is_valid_tile_position(self, tile: BoardTile) -> bool:
        return None not in tile.position

    def _calculate_orthogonal_directions(self, dir_0: float) -> List[float]:
        directions = [dir_0]
        current_dir = dir_0

        for _ in range(3):
            current_dir = normalize_angle(current_dir + HALF_PI)
            directions.append(current_dir)

        return directions

    def _get_vertex_positions(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        return [
            ((0, 0), (3, 0)),  # Top-left vertex
            ((1, 0), (0, 1)),  # Top-right vertex
            ((1, 1), (1, 2)),  # Bottom-right vertex
            ((0, 1), (2, 3)),  # Bottom-left vertex
        ]

    @classmethod
    def _extrapolate_last_point(cls, points: List[List[int]]) -> List[int]:
        min_idx, max_idx = cls._find_point_range(points)

        vector = cls._calculate_extrapolation_vector(points, min_idx, max_idx)
        base_point = points[min_idx]

        return [base_point[i] + vector[i] for i in range(2)]

    @classmethod
    def _calculate_extrapolation_vector(
        cls, points: List[List[int]], min_idx: int, max_idx: int
    ) -> List[int]:
        vector_init_len = max_idx - min_idx
        vector_final_len = 8 - min_idx

        vector = [points[max_idx][i] - points[min_idx][i] for i in range(2)]

        scale_factor = vector_final_len / vector_init_len
        return [int(v * scale_factor) for v in vector]

    @staticmethod
    def _find_point_range(points: List[List[int]]) -> Tuple[int, int]:
        min_idx, max_idx = 8, 0
        for i, point in enumerate(points):
            if point is not None:
                min_idx = min(min_idx, i)
                max_idx = max(max_idx, i)
        return min_idx, max_idx

    def _calculate_vertexes(self) -> None:
        self._set_known_vertexes()
        self._calculate_missing_vertexes()

    def _set_known_vertexes(self) -> None:
        vertex_positions = [((0, 0), 0), ((8, 0), 1), ((8, 8), 2), ((0, 8), 3)]

        for (x, y), idx in vertex_positions:
            if self.points[x][y] is not None:
                self.vertexes[idx] = self.points[x][y]

    def _calculate_missing_vertexes(self) -> None:
        vertex_data = [
            # vertex_idx, points_pair1, points_pair2, target_position
            (0, self.points[0], 0, (0, 0)),  # top-left vertex
            (1, self.points[8], 0, (8, 0)),  # top-right vertex
            (2, self.points[8], 8, (8, 8)),  # bottom-right vertex
            (3, self.points[0], 8, (0, 8)),  # bottom-left vertex
        ]

        for vertex_idx, row_points, col_idx, target_pos in vertex_data:
            if self.vertexes[vertex_idx] is not None:
                continue

            # Get points from rows and columns
            points1 = [v[col_idx] for v in self.points]
            points2 = row_points

            if vertex_idx in [0, 3]:
                points1 = points1[::-1]
            if vertex_idx in [0, 1]:
                points2 = points2[::-1]

            # Calculate vertex position
            pred1 = self._extrapolate_last_point(points1)
            pred2 = self._extrapolate_last_point(points2)
            vertex = get_avg_pos([pred1, pred2])

            # Set vertex position
            self.vertexes[vertex_idx] = vertex
            self.points[target_pos[0]][target_pos[1]] = vertex

    def _interpolate_borders(self) -> None:
        # Extract border points
        border_01 = [v[0] for v in self.points]  # Left border
        border_12 = self.points[8]  # Bottom border
        border_32 = [v[8] for v in self.points]  # Right border
        border_03 = self.points[0]  # Top border

        border_data = [
            (border_01, 0, True),  # (points, fixed_index, is_vertical)
            (border_12, 8, False),
            (border_32, 8, True),
            (border_03, 0, False),
        ]

        for border_points, fixed_idx, is_vertical in border_data:
            self._interpolate_border(border_points, fixed_idx, is_vertical)

    def _interpolate_border(
        self, border_points: List[List[int]], fixed_idx: int, is_vertical: bool
    ) -> None:
        for i in range(1, len(border_points) - 1):
            if border_points[i] is not None:
                continue

            # Get points for averaging
            averaging_points = self._get_averaging_points(border_points, i)

            # Get extrapolation points
            if is_vertical:
                extrapolation_points = (
                    self.points[i][::-1] if fixed_idx == 0 else self.points[i]
                )
            else:
                extrapolation_points = (
                    [row[i] for row in self.points][::-1]
                    if fixed_idx == 0
                    else [row[i] for row in self.points]
                )

            # Calculate final position
            extrapolation_value = self._extrapolate_last_point(extrapolation_points)
            final_position = get_avg_pos(
                [get_avg_pos(averaging_points), extrapolation_value]
            )

            # Update points
            if is_vertical:
                self.points[i][fixed_idx] = final_position
            else:
                self.points[fixed_idx][i] = final_position
            border_points[i] = final_position

    def _get_averaging_points(
        self, points: List[List[int]], current_idx: int
    ) -> List[List[int]]:
        averaging_points = []
        averaging_points.append(points[current_idx - 1])

        for j in range(current_idx + 1, len(points)):
            if points[j] is not None:
                averaging_points.append(points[j])
                break

        return averaging_points

    def _interpolate_inner_points(self) -> None:
        for i in range(1, len(self.points) - 1):
            for j in range(1, len(self.points[i]) - 1):
                if self.points[i][j] is None:
                    self._interpolate_point(i, j)

    def _interpolate_point(self, i: int, j: int) -> None:
        # Get points in same row
        row_points = self._get_next_valid_points(
            self.points[i], j, self.points[i][j - 1]
        )

        # Get points in same column
        column = [row[j] for row in self.points]
        col_points = self._get_next_valid_points(column, i, self.points[i - 1][j])

        # Calculate final position
        self.points[i][j] = get_avg_pos(
            [get_avg_pos(row_points), get_avg_pos(col_points)]
        )

    def _get_next_valid_points(
        self, points: List[List[int]], current_idx: int, prev_point: List[int]
    ) -> List[List[int]]:
        result = [prev_point]

        for k in range(current_idx + 1, len(points)):
            if points[k] is not None:
                result.append(points[k])
                break

        return result

    def is_00_white(self, config: Optional[BoardConfig] = None) -> bool:
        pt = get_avg_pos(
            [self.points[0][0], self.points[0][1], self.points[1][1], self.points[1][0]]
        )

        sample = Board.frame[
            (pt[1] - config.radius) : (pt[1] + config.radius),
            (pt[0] - config.radius) : (pt[0] + config.radius),
        ]
        sample_avg_bgr = get_avg_color(sample)
        return not (
            distance_from_color(sample_avg_bgr, config.dark_field_bgr)
            < distance_from_color(sample_avg_bgr, config.light_field_bgr)
            or distance_from_color(sample_avg_bgr, config.orange_bgr)
            <= config.color_dist_thresh
            or distance_from_color(sample_avg_bgr, config.blue_bgr)
            <= config.color_dist_thresh
        )

    @staticmethod
    def _get_mirrored_2d_matrix_y_axis(matrix):
        new_matrix = []
        col_num = len(matrix)
        for c in range(0, col_num):
            new_matrix.append(matrix[col_num - 1 - c])
        return new_matrix


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
