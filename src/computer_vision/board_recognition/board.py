"""Module for detecting and representing a checkerboard."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

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
    compute_average_bgr_color,
    compute_average_hsv_color,
    convert_bgr_to_hsv,
    euclidean_hsv_distance,
    compute_centroid,
    normalize_radians,
)

from .board_tile import BoardTile
from .contour_detector import ContourDetector
from .tile_grid import TileGrid


class Board:
    """Represents a detected checkerboard and provides drawing utilities."""

    def __init__(
        self,
        frame: np.ndarray,
        tile_grid: TileGrid,
    ) -> None:
        """Initialize the Board with a frame and detected tile grid.

        Args:
            frame: The source image frame.
            tile_grid: The grid of detected board tiles.
        """
        self.frame: np.ndarray = frame
        self.tile_grid: TileGrid = tile_grid
        self.points: List[List[Optional[tuple[int, int]]]] = [
            [None for _ in range(9)] for _ in range(9)
        ]
        self.vertices: List[Optional[tuple[int, int]]] = [None] * 4

    @property
    def tiles(self) -> List[BoardTile]:
        """Return the list of detected tiles."""
        return self.tile_grid.tiles

    @classmethod
    def from_image(
        cls,
        image: np.ndarray,
        contour_detector: ContourDetector,
        recognition_config: Optional[RecognitionConfig] = None,
    ) -> "Board":
        """Factory method to create a fully detected board from an image.

        Args:
            image: Input BGR image.
            contour_detector: Instance of ContourDetector.
            recognition_config: Optional configuration override.

        Returns:
            A fully initialized Board instance.

        Raises:
            BoardDetectionError: If detection fails.
        """
        config = recognition_config or RecognitionConfig()
        frame = image.copy()

        try:
            contours = contour_detector.detect(frame, config)
            tile_grid = TileGrid.from_contours(frame, contours)
            board = cls(frame=frame, tile_grid=tile_grid)
            board._initialize_board()
            return board
        except (BoardDetectionError, InsufficientDataError):
            raise
        except Exception as exc:
            raise BoardDetectionError(
                "Unknown error occurred while trying to detect board"
            ) from exc

    @classmethod
    def detect_board(
        cls,
        image: np.ndarray,
        recognition_config: Optional[RecognitionConfig] = None,
        contour_detector: Optional[ContourDetector] = None,
    ) -> "Board":
        """Backward-compatible entrypoint for board detection.

        Args:
            image: Input BGR image.
            recognition_config: Optional configuration override.
            contour_detector: Optional pre-configured detector.

        Returns:
            A fully initialized Board instance.
        """
        from .board_detector import BoardDetector

        detector = BoardDetector(
            contour_detector=contour_detector,
            recognition_config=recognition_config,
        )
        return detector.detect(image)

    def get_frame_copy(self) -> np.ndarray:
        """Return a copy of the board frame."""
        return self.frame.copy()

    def _initialize_board(self) -> None:
        """Orchestrate the board initialization pipeline."""
        start_tile = self._find_start_tile()
        self._process_start_tile(start_tile)
        self._process_board_points(start_tile)
        self._draw_border_points()

        self._interpolate_borders()
        self._interpolate_inner_points()

        self.points = self._mirror_matrix_y_axis(self.points)
        self._draw_board_grid()

    def _find_start_tile(self) -> BoardTile:
        """Find the anchor tile with 4 neighbors to start indexing.

        Returns:
            The starting tile.

        Raises:
            NoStartTileError: If no tile with 4 neighbors is found.
        """
        start_tile = next(
            (tile for tile in self.tiles if tile.neighbors_count == 4), None
        )
        if start_tile is None:
            raise NoStartTileError("Couldn't find starting tile")
        return start_tile

    def _process_start_tile(self, start_tile: BoardTile) -> None:
        """Assign grid indexes to the start tile and draw its coordinates.

        Args:
            start_tile: The anchor tile.

        Raises:
            BoardDetectionError: If processing fails.
        """
        try:
            self._assign_start_tile_indexes(start_tile)
            self._draw_tile_coordinates(start_tile)
        except InsufficientDataError:
            raise
        except Exception as exc:
            raise BoardDetectionError(
                "Error occurred while trying to process start tile"
            ) from exc

    def _draw_tile_coordinates(self, tile: BoardTile) -> None:
        """Draw the grid coordinates on the tile center.

        Args:
            tile: The tile to annotate.
        """
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
        """Propagate indexes to all tiles and compute board points.

        Args:
            start_tile: The anchor tile.
        """
        self._propagate_all_tile_indexes(start_tile)

        primary_dir = start_tile.get_primary_direction()
        if primary_dir is None:
            raise InsufficientDataError(
                "Couldn't determine indexing direction for start tile"
            )
        self._populate_known_board_points(primary_dir)
        self._compute_vertices()

    def _draw_board_grid(self) -> None:
        """Draw the inner grid lines of the board."""
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
        """Draw the outer border vertices of the board."""
        for vertex in self.vertices:
            if vertex is not None:
                cv.circle(self.frame, vertex, 3, (0, 255, 0), -1)

    @staticmethod
    def _calculate_directions(start_tile: BoardTile) -> Dict[str, float]:
        """Compute all primary and diagonal direction angles.

        Args:
            start_tile: The anchor tile.

        Returns:
            Dictionary mapping direction keys to angles in radians.

        Raises:
            InsufficientDataError: If primary direction is missing.
        """
        base_direction = start_tile.get_primary_direction()
        if base_direction is None:
            raise InsufficientDataError(
                "Couldn't determine base direction for start tile"
            )

        return {
            "dir_0": base_direction,
            "dir_01": normalize_radians(base_direction + QUARTER_PI),
            "dir_1": normalize_radians(base_direction + HALF_PI),
            "dir_12": normalize_radians(base_direction + HALF_PI + QUARTER_PI),
            "dir_2": normalize_radians(base_direction + math.pi),
            "dir_23": normalize_radians(base_direction + math.pi + QUARTER_PI),
            "dir_3": normalize_radians(base_direction + math.pi + HALF_PI),
            "dir_30": normalize_radians(
                base_direction + math.pi + HALF_PI + QUARTER_PI
            ),
        }

    @classmethod
    def _assign_start_tile_indexes(cls, start_tile: BoardTile) -> None:
        """Determine the grid position of the start tile.

        Args:
            start_tile: The anchor tile.

        Raises:
            InsufficientDataError: If board edges are not fully visible.
        """
        directions = cls._calculate_directions(start_tile)

        dir_1_steps = cls._count_steps_in_direction(
            start_tile,
            directions["dir_01"],
            directions["dir_12"],
            directions["dir_1"],
            1,
        )
        dir_3_steps = cls._count_steps_in_direction(
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

        dir_2_steps = cls._count_steps_in_direction(
            start_tile,
            directions["dir_12"],
            directions["dir_23"],
            directions["dir_2"],
            2,
        )
        dir_0_steps = cls._count_steps_in_direction(
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
    def _count_steps_in_direction(
        tile: BoardTile, start_rad: float, end_rad: float, dir_rad: float, dir_idx: int
    ) -> int:
        """Count tiles in a specific direction from a starting tile.

        Args:
            tile: Starting tile.
            start_rad: Start angle of the search sector.
            end_rad: End angle of the search sector.
            dir_rad: Primary direction angle.
            dir_idx: Direction index (0-3).

        Returns:
            Number of steps found.
        """
        neighbor = tile.get_neighbor_in_angle_range(start_rad, end_rad)
        if neighbor is None:
            return 0
        return tile.get_steps_in_direction(dir_rad, dir_idx)

    @staticmethod
    def _propagate_all_tile_indexes(start_tile: BoardTile) -> None:
        """Propagate grid indexes from the start tile to all connected tiles.

        Args:
            start_tile: The anchor tile.

        Raises:
            InsufficientDataError: If primary direction is missing.
        """
        primary_dir = start_tile.get_primary_direction()
        if primary_dir is None:
            raise InsufficientDataError(
                "Couldn't determine indexing direction for start tile"
            )
        start_tile.propagate_indexes(primary_dir)

    def _populate_known_board_points(self, primary_dir: float) -> None:
        """Map tile vertices to the 9x9 board grid points.

        Args:
            primary_dir: Primary direction angle in radians.
        """
        directions = self._compute_orthogonal_directions(primary_dir)
        vertex_positions = self._get_vertex_positions()

        for tile in self.tiles:
            if None in tile.position:
                continue

            tile_x, tile_y = tile.position
            assert tile_x is not None and tile_y is not None

            tile_x = int(tile_x)
            tile_y = int(tile_y)

            for pos, dir_range in vertex_positions:
                x = tile_x + pos[0]
                y = tile_y + pos[1]

                if x < 0 or x >= len(self.points) or y < 0 or y >= len(self.points[0]):
                    continue

                if self.points[x][y] is None:
                    start_dir, end_dir = (
                        directions[dir_range[0]],
                        directions[dir_range[1]],
                    )
                    vertex = tile.get_vertex_in_angle_range(start_dir, end_dir)
                    if vertex is not None:
                        self.points[x][y] = (vertex[0], vertex[1])
                    else:
                        self.points[x][y] = None

    def _compute_orthogonal_directions(self, dir_0: float) -> List[float]:
        """Compute the 4 orthogonal directions starting from dir_0.

        Args:
            dir_0: Base direction angle.

        Returns:
            List of 4 angles in radians.
        """
        directions = [dir_0]
        current_dir = dir_0
        for _ in range(3):
            current_dir = normalize_radians(current_dir + HALF_PI)
            directions.append(current_dir)
        return directions

    @staticmethod
    def _get_vertex_positions() -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Return relative positions and direction ranges for tile vertices.

        Returns:
            List of tuples containing (relative_position, direction_range).
        """
        return [
            ((0, 0), (3, 0)),  # top-left
            ((1, 0), (0, 1)),  # top-right
            ((1, 1), (1, 2)),  # bottom-right
            ((0, 1), (2, 3)),  # bottom-left
        ]

    @classmethod
    def _extrapolate_last_point(
        cls, points: List[Optional[tuple[int, int]]]
    ) -> tuple[int, int]:
        """Extrapolate the last point in a sequence based on the trend.

        Args:
            points: List of 2D points.

        Returns:
            Extrapolated point coordinates.

        Raises:
            InsufficientDataError: If extrapolation fails.
        """
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
        """Calculate the extrapolation vector from known points.

        Args:
            points: List of 2D points.
            min_idx: Index of the first known point.
            max_idx: Index of the last known point.

        Returns:
            Scaled extrapolation vector.

        Raises:
            InsufficientDataError: If required points are missing.
        """
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
        """Find the range of indices containing non-None points.

        Args:
            points: List of 2D points.

        Returns:
            Tuple of (min_index, max_index).
        """
        min_idx, max_idx = 8, 0
        for i, point in enumerate(points):
            if point is not None:
                min_idx = min(min_idx, i)
                max_idx = max(max_idx, i)
        return min_idx, max_idx

    def _compute_vertices(self) -> None:
        """Calculate all 4 outer vertices of the board."""
        self._assign_known_vertices()
        self._compute_missing_vertices()

    def _assign_known_vertices(self) -> None:
        """Assign known grid points to the board vertices."""
        vertex_positions = [((0, 0), 0), ((8, 0), 1), ((8, 8), 2), ((0, 8), 3)]
        for (x, y), idx in vertex_positions:
            if self.points[x][y] is not None:
                self.vertices[idx] = self.points[x][y]

    def _compute_missing_vertices(self) -> None:
        """Extrapolate missing board vertices from known points."""
        vertex_data = [
            (0, self.points[0], 0, (0, 0)),
            (1, self.points[8], 0, (8, 0)),
            (2, self.points[8], 8, (8, 8)),
            (3, self.points[0], 8, (0, 8)),
        ]

        for vertex_idx, row_points, col_idx, target_pos in vertex_data:
            if self.vertices[vertex_idx] is not None:
                continue

            points1: List[Optional[tuple[int, int]]] = [v[col_idx] for v in self.points]
            points2: List[Optional[tuple[int, int]]] = row_points

            if vertex_idx in [0, 3]:
                points1 = points1[::-1]
            if vertex_idx in [0, 1]:
                points2 = points2[::-1]

            pred1 = self._extrapolate_last_point(points1)
            pred2 = self._extrapolate_last_point(points2)
            vertex = compute_centroid([pred1, pred2])

            self.vertices[vertex_idx] = vertex
            self.points[target_pos[0]][target_pos[1]] = vertex

    def _interpolate_borders(self) -> None:
        """Interpolate missing points along the 4 board borders."""
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
        """Interpolate missing points on a single border.

        Args:
            border_points: List of points along the border.
            fixed_idx: Fixed coordinate index (row or column).
            is_vertical: Whether the border is vertical.
        """
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
            final_position = compute_centroid(
                [compute_centroid(averaging_points), extrapolation_value]
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
        """Find neighboring points to average for interpolation.

        Args:
            points: List of 2D points.
            current_idx: Index of the missing point.

        Returns:
            List of valid neighboring points.
        """
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
        """Interpolate missing points in the inner 7x7 grid."""
        for i in range(1, len(self.points) - 1):
            for j in range(1, len(self.points[i]) - 1):
                if self.points[i][j] is None:
                    self._interpolate_point(i, j)

    def _interpolate_point(self, i: int, j: int) -> None:
        """Interpolate a single missing point using row and column neighbors.

        Args:
            i: Row index.
            j: Column index.
        """
        prev_row = self.points[i][j - 1]
        prev_col = self.points[i - 1][j]
        if prev_row is None or prev_col is None:
            return

        row_points = self._get_next_valid_points(self.points[i], j, prev_row)
        column = [row[j] for row in self.points]
        col_points = self._get_next_valid_points(column, i, prev_col)

        self.points[i][j] = compute_centroid(row_points + col_points)

    @staticmethod
    def _get_next_valid_points(
        points: List[Optional[tuple[int, int]]],
        current_idx: int,
        prev_point: tuple[int, int],
    ) -> List[tuple[int, int]]:
        """Find the next valid point in a sequence for interpolation.

        Args:
            points: List of 2D points.
            current_idx: Current index.
            prev_point: Previous valid point.

        Returns:
            List containing prev_point and the next valid point.
        """
        result = [prev_point]

        for k in range(current_idx + 1, len(points)):
            point = points[k]
            if point is not None:
                result.append(point)
                break

        return result

    def is_00_white(self, color_config: ColorConfig, radius: int = 4) -> bool:
        """Determine if the top-left board field (0,0) is white.

        Args:
            color_config: Color configuration for comparison.
            radius: Sampling radius around the center.

        Returns:
            True if the field is white, False otherwise.
        """
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

        pt = compute_centroid([top_left, top_right, bottom_right, bottom_left])

        frame_height, frame_width = self.frame.shape[:2]
        x_min = max(0, pt[0] - radius)
        x_max = min(frame_width, pt[0] + radius)
        y_min = max(0, pt[1] - radius)
        y_max = min(frame_height, pt[1] + radius)

        if x_min >= x_max or y_min >= y_max:
            return False

        sample = self.frame[y_min:y_max, x_min:x_max]
        # Use median HSV for robustness to noise
        from src.common.utils import compute_median_hsv_color, hue_diff

        sample_median_hsv = compute_median_hsv_color(sample)

        # Reject if sample is too dark, unsaturated, or colored (checker piece on tile)
        s_min, v_min = 30, 30
        if sample_median_hsv[1] < s_min or sample_median_hsv[2] < v_min:
            return False

        # Use brightness as primary distinguisher: white is much brighter than black
        # Threshold is set empirically at midpoint of typical white/black brightness values
        return sample_median_hsv[2] > 120

    @staticmethod
    def _mirror_matrix_y_axis(
        matrix: List[List[Optional[tuple[int, int]]]],
    ) -> List[List[Optional[tuple[int, int]]]]:
        """Mirror a 2D matrix along the Y-axis.

        Args:
            matrix: Input 2D matrix.

        Returns:
            Mirrored matrix.
        """
        return [matrix[len(matrix) - 1 - c] for c in range(len(matrix))]
