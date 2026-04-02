from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import cv2 as cv
import numpy as np

from src.common.configs import ColorConfig, RecognitionConfig
from src.common.exceptions import (
    BoardDetectionError,
    InsufficientDataError,
    NoStartTileError,
)
from src.common.utils import (
    HALF_PI,
    QUARTER_PI,
    distance_from_color,
    get_avg_color,
    get_avg_pos,
    normalize_angle,
)

from .board_tile import BoardTile
from .contours import ContourDetector


class Board:
    """Detected board model + drawing helpers."""

    def __init__(self, frame: np.ndarray) -> None:
        self.frame: np.ndarray = frame
        self.tiles: List[BoardTile] = []
        self.points: List[List[Optional[tuple[int, int]]]] = [
            [None for _ in range(9)] for _ in range(9)
        ]
        self.vertexes: List[Optional[tuple[int, int]]] = [None] * 4

    @classmethod
    def from_image(
        cls,
        image: np.ndarray,
        contour_processor: ContourDetector,
        recognition_config: Optional[RecognitionConfig] = None,
    ) -> "Board":
        """Factory creating a fully-detected board from an image."""
        config = recognition_config or RecognitionConfig()
        board = cls(frame=image.copy())

        try:
            contours = contour_processor.get_contours(board.frame, config)
            BoardTile.create_tiles(board.frame, contours)
            board.tiles = [tile for tile in BoardTile.tiles]
            board._initialize_board()
            return board
        except (BoardDetectionError, InsufficientDataError):
            raise
        except Exception as exc:
            raise BoardDetectionError(
                "Unknown Error occurred while trying to detect board"
            ) from exc

    @classmethod
    def detect_board(
        cls,
        image: np.ndarray,
        recognition_config: Optional[RecognitionConfig] = None,
        contour_processor: Optional[ContourDetector] = None,
    ) -> "Board":
        """Backward-compatible entrypoint.

        Kept for compatibility with existing call sites, but does not use any
        singleton board state.
        """
        detector = BoardDetector(
            contour_processor=contour_processor,
            recognition_config=recognition_config,
        )
        return detector.detect(image)

    def get_frame_copy(self) -> np.ndarray:
        """Return a copy of board frame."""
        return self.frame.copy()

    def _initialize_board(self) -> None:
        """Initialize board detection from prepared tiles."""
        start_tile = self._find_start_tile()
        self._process_start_tile(start_tile)
        self._process_board_points(start_tile)
        self._draw_border_points()

        self._interpolate_borders()
        self._interpolate_inner_points()

        self.points = self._get_mirrored_2d_matrix_y_axis(self.points)
        self._draw_board()

    def _find_start_tile(self) -> BoardTile:
        """Find starting tile used as indexing anchor."""
        start_tile = next(
            (tile for tile in self.tiles if tile.neighbors_count == 4), None
        )
        if start_tile is None:
            raise NoStartTileError("Couldn't find starting tile")
        return start_tile

    def _process_start_tile(self, start_tile: BoardTile) -> None:
        """Set start tile index and draw index label."""
        try:
            self._set_index_of_start_tile(start_tile)
            self._draw_tile_coordinates(start_tile)
        except InsufficientDataError:
            raise
        except Exception as exc:
            raise BoardDetectionError(
                "Error occured while trying to process start tile"
            ) from exc

    def _draw_tile_coordinates(self, tile: BoardTile) -> None:
        cv.putText(
            self.frame,
            f"{tile.position[0]},{tile.position[1]}",
            (tile.center[0], tile.center[1]),
            cv.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv.LINE_AA,
        )

    def _process_board_points(self, start_tile: BoardTile) -> None:
        self._set_all_tiles_indexes(start_tile)

        dir_0 = start_tile.get_dir_0_radians()
        if dir_0 is None:
            raise InsufficientDataError(
                "Couldn't determine indexing direction for start tile"
            )
        self._set_all_known_board_points(dir_0)
        self._calculate_vertexes()

    def _draw_board(self) -> None:
        """Draw inner board lines."""
        for i in range(9):
            for j in range(9):
                if i == 8:
                    continue

                start_point = self.points[i][j]
                end_point = self.points[i + 1][j]
                if start_point is None or end_point is None:
                    continue

                cv.line(
                    self.frame,
                    start_point,
                    end_point,
                    (0, 255, 0),
                    1,
                )

                if j == 8:
                    continue

                start_point = self.points[i][j]
                end_point = self.points[i][j + 1]
                if start_point is None or end_point is None:
                    continue

                cv.line(
                    self.frame,
                    start_point,
                    end_point,
                    (0, 255, 0),
                    1,
                )

    def _draw_border_points(self) -> None:
        """Draw board vertex points."""
        for vertex in self.vertexes:
            if vertex is not None:
                cv.circle(self.frame, vertex, 3, (0, 255, 0), -1)

    @staticmethod
    def _calculate_directions(start_tile: BoardTile) -> Dict[str, float]:
        base_direction = start_tile.get_dir_0_radians()
        if base_direction is None:
            raise InsufficientDataError(
                "Couldn't determine base direction for start tile"
            )

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
        directions = cls._calculate_directions(start_tile)

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

    @staticmethod
    def _set_all_tiles_indexes(start_tile: BoardTile) -> None:
        dir_0 = start_tile.get_dir_0_radians()
        if dir_0 is None:
            raise InsufficientDataError(
                "Couldn't determine indexing direction for start tile"
            )
        start_tile.index_neighbors(dir_0)

    def _set_all_known_board_points(self, dir_0: float) -> None:
        directions = self._calculate_orthogonal_directions(dir_0)
        vertex_positions = self._get_vertex_positions()

        for tile in self.tiles:
            if None in tile.position:
                continue

            tile_x, tile_y = tile.position
            assert tile_x is not None and tile_y is not None

            # tile.position is guaranteed to be ints after the guard above
            tile_x = int(tile_x)
            tile_y = int(tile_y)

            for pos, dir_range in vertex_positions:
                x = tile_x + pos[0]
                y = tile_y + pos[1]

                if self.points[x][y] is None:
                    start_dir, end_dir = (
                        directions[dir_range[0]],
                        directions[dir_range[1]],
                    )
                    vertex = tile.get_vertex_in_rad_range(start_dir, end_dir)
                    if vertex is not None:
                        self.points[x][y] = (vertex[0], vertex[1])
                    else:
                        self.points[x][y] = None

    def _calculate_orthogonal_directions(self, dir_0: float) -> List[float]:
        directions = [dir_0]
        current_dir = dir_0
        for _ in range(3):
            current_dir = normalize_angle(current_dir + HALF_PI)
            directions.append(current_dir)
        return directions

    @staticmethod
    def _get_vertex_positions() -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        return [
            ((0, 0), (3, 0)),  # top-left
            ((1, 0), (0, 1)),  # top-right
            ((1, 1), (1, 2)),  # bottom-right
            ((0, 1), (2, 3)),  # bottom-left
        ]

    @classmethod
    def _extrapolate_last_point(cls, points: List[Optional[tuple[int, int]]]) -> tuple[int, int]:
        min_idx, max_idx = cls._find_point_range(points)
        if min_idx == max_idx:
            point = points[min_idx]
            return (0, 0) if point is None else point

        vector = cls._calculate_extrapolation_vector(points, min_idx, max_idx)
        base_point = points[min_idx]
        if base_point is None:
            raise InsufficientDataError("Cannot extrapolate from empty base point")

        return (base_point[0] + vector[0], base_point[1] + vector[1])

    @classmethod
    def _calculate_extrapolation_vector(
        cls, points: List[Optional[tuple[int, int]]], min_idx: int, max_idx: int
    ) -> tuple[int, int]:
        start_point = points[min_idx]
        end_point = points[max_idx]
        if start_point is None or end_point is None:
            raise InsufficientDataError("Cannot calculate extrapolation vector")

        vector_init_len = max_idx - min_idx
        if vector_init_len == 0:
            return (0, 0)

        vector_final_len = 8 - min_idx
        vector = [end_point[i] - start_point[i] for i in range(2)]
        scale_factor = vector_final_len / vector_init_len
        return (int(vector[0] * scale_factor), int(vector[1] * scale_factor))

    @staticmethod
    def _find_point_range(points: List[Optional[tuple[int, int]]]) -> Tuple[int, int]:
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
            (0, self.points[0], 0, (0, 0)),
            (1, self.points[8], 0, (8, 0)),
            (2, self.points[8], 8, (8, 8)),
            (3, self.points[0], 8, (0, 8)),
        ]

        for vertex_idx, row_points, col_idx, target_pos in vertex_data:
            if self.vertexes[vertex_idx] is not None:
                continue

            points1: List[Optional[tuple[int, int]]] = [v[col_idx] for v in self.points]
            points2: List[Optional[tuple[int, int]]] = row_points

            if vertex_idx in [0, 3]:
                points1 = points1[::-1]
            if vertex_idx in [0, 1]:
                points2 = points2[::-1]

            pred1 = self._extrapolate_last_point(points1)
            pred2 = self._extrapolate_last_point(points2)
            vertex = get_avg_pos([pred1, pred2])

            self.vertexes[vertex_idx] = vertex
            self.points[target_pos[0]][target_pos[1]] = vertex

    def _interpolate_borders(self) -> None:
        border_01 = [v[0] for v in self.points]
        border_12 = self.points[8]
        border_32 = [v[8] for v in self.points]
        border_03 = self.points[0]

        border_data = [
            (border_01, 0, True),
            (border_12, 8, False),
            (border_32, 8, True),
            (border_03, 0, False),
        ]

        for border_points, fixed_idx, is_vertical in border_data:
            self._interpolate_border(border_points, fixed_idx, is_vertical)

    def _interpolate_border(
        self,
        border_points: List[Optional[tuple[int, int]]],
        fixed_idx: int,
        is_vertical: bool,
    ) -> None:
        for i in range(1, len(border_points) - 1):
            if border_points[i] is not None:
                continue

            averaging_points = self._get_averaging_points(border_points, i)

            if is_vertical:
                extrapolation_points = (
                    self.points[i][::-1] if fixed_idx == 0 else self.points[i]
                )
            else:
                column = [row[i] for row in self.points]
                extrapolation_points = column[::-1] if fixed_idx == 0 else column

            extrapolation_value = self._extrapolate_last_point(extrapolation_points)
            final_position = get_avg_pos(
                [get_avg_pos(averaging_points), extrapolation_value]
            )

            if is_vertical:
                self.points[i][fixed_idx] = final_position
            else:
                self.points[fixed_idx][i] = final_position
            border_points[i] = final_position

    @staticmethod
    def _get_averaging_points(
        points: List[Optional[tuple[int, int]]], current_idx: int
    ) -> List[tuple[int, int]]:
        averaging_points: List[tuple[int, int]] = []

        left = points[current_idx - 1]
        if left is not None:
            averaging_points.append(left)

        for j in range(current_idx + 1, len(points)):
            point = points[j]
            if point is not None:
                averaging_points.append(point)
                break

        if not averaging_points:
            return [(0, 0)]
        return averaging_points

    def _interpolate_inner_points(self) -> None:
        for i in range(1, len(self.points) - 1):
            for j in range(1, len(self.points[i]) - 1):
                if self.points[i][j] is None:
                    self._interpolate_point(i, j)

    def _interpolate_point(self, i: int, j: int) -> None:
        prev_row = self.points[i][j - 1]
        prev_col = self.points[i - 1][j]
        if prev_row is None or prev_col is None:
            return

        row_points = self._get_next_valid_points(self.points[i], j, prev_row)
        column = [row[j] for row in self.points]
        col_points = self._get_next_valid_points(column, i, prev_col)

        self.points[i][j] = get_avg_pos(
            [get_avg_pos(row_points), get_avg_pos(col_points)]
        )

    @staticmethod
    def _get_next_valid_points(
        points: List[Optional[tuple[int, int]]], current_idx: int, prev_point: tuple[int, int]
    ) -> List[tuple[int, int]]:
        result = [prev_point]

        for k in range(current_idx + 1, len(points)):
            point = points[k]
            if point is not None:
                result.append(point)
                break

        return result

    def is_00_white(self, color_config: ColorConfig, radius: int = 4) -> bool:
        top_left = self.points[0][0]
        top_right = self.points[0][1]
        bottom_right = self.points[1][1]
        bottom_left = self.points[1][0]
        if (
            top_left is None
            or top_right is None
            or bottom_right is None
            or bottom_left is None
        ):
            return False

        pt = get_avg_pos([top_left, top_right, bottom_right, bottom_left])

        frame_height, frame_width = self.frame.shape[:2]
        x_min = max(0, pt[0] - radius)
        x_max = min(frame_width, pt[0] + radius)
        y_min = max(0, pt[1] - radius)
        y_max = min(frame_height, pt[1] + radius)

        if x_min >= x_max or y_min >= y_max:
            return False

        sample = self.frame[y_min:y_max, x_min:x_max]
        sample_avg_bgr = get_avg_color(sample)
        return not (
            distance_from_color(sample_avg_bgr, color_config["black"])
            < distance_from_color(sample_avg_bgr, color_config["white"])
            or distance_from_color(sample_avg_bgr, color_config["orange"]) <= 60
            or distance_from_color(sample_avg_bgr, color_config["blue"]) <= 60
        )

    @staticmethod
    def _get_mirrored_2d_matrix_y_axis(
        matrix: List[List[Optional[tuple[int, int]]]],
    ) -> List[List[Optional[tuple[int, int]]]]:
        return [matrix[len(matrix) - 1 - c] for c in range(len(matrix))]


class BoardDetector:
    """Dependency-injected board detection service."""

    def __init__(
        self,
        contour_processor: Optional[ContourDetector] = None,
        recognition_config: Optional[RecognitionConfig] = None,
    ) -> None:
        self.contour_processor = contour_processor or ContourDetector()
        self.recognition_config = recognition_config or RecognitionConfig()

    def detect(
        self, image: np.ndarray, recognition_config: Optional[RecognitionConfig] = None
    ) -> Board:
        config = recognition_config or self.recognition_config
        return Board.from_image(
            image=image,
            contour_processor=self.contour_processor,
            recognition_config=config,
        )


if __name__ == "__main__":
    cap = cv.VideoCapture(0)
    detector = BoardDetector()

    while True:
        ret, img = cap.read()
        if not ret:
            break

        try:
            board = detector.detect(img)
            print(len(BoardTile.tiles))
            draw_image = board.get_frame_copy()
            cv.imshow("RESULT", draw_image)
        except (BoardDetectionError, InsufficientDataError, NoStartTileError) as exc:
            print(exc)

        if cv.waitKey(1) == ord("q"):
            break

    cap.release()
    cv.destroyAllWindows()
