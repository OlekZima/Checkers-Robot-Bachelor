"""Module for representing a tile on the board for the cv2 processing."""

import math
from typing import ClassVar, List, Optional, Self, Tuple, Dict

import cv2
import numpy as np
from src.common.utilities import (
    get_avg_pos,
    HALF_PI,
    THREE_QUARTER_PI,
    TWO_PI,
    QUARTER_PI,
)

from .contours_recognition import ContourProcessor


class BoardTile:
    """Class representing a tile on the board for the cv2 processing."""

    tiles: ClassVar[np.ndarray[Self]] = np.array([])
    _frame: ClassVar[Optional[np.ndarray]] = None
    NEIGHBORS_KEYS: ClassVar[List[str]] = ["n01", "n12", "n23", "n30"]

    def __init__(self, points: Optional[List[List[int]]] = None) -> None:
        """Initializes the BoardTile.
        Creates a tile with 4 vertexes and a center point.
        Each tile has 4 neighbors that share 2 vertexes with this tile.
        Neigbors are stored in a dictionary with keys "n01", "n12", "n23", "n30".

        Key "n01" means that the neighbor shares vertexes[0] and vertexes[1] points with this tile.


        Args:
            points (Optional[List[List[int]]], optional):
                List of points where each point is represent by list of two int. Defaults to None.
        """
        self.vertexes = [[0, 0] for _ in range(4)] if points is None else points

        self.center = get_avg_pos(points)

        self.neighbors: Dict[str, Optional[Self]] = {
            key: None for key in self.NEIGHBORS_KEYS
        }
        self.neighbors_count = 0

        self.position: Tuple[Optional[int], Optional[int]] = (
            None,
            None,
        )

        self.was_checked_in_dir_idx = [False, False, False, False]

    @classmethod
    def create_tiles(cls, image: np.ndarray, contours: np.ndarray) -> None:
        """Creates tiles from the image and contours and stores them in the class variables.

        Args:
            image (np.ndarray): Image on which the tiles are located.
            contours (np.ndarray): Contours detected on the image of the tiles.
        """
        cls._frame = image
        cls.tiles = np.array([])

        # creating tiles from all contours
        for cnt in contours:
            points = [cnt[i][0] for i in range(4)]
            cls.tiles = np.append(cls.tiles, BoardTile(points=points))

        # keepeing tiles that have at least 1 neighbor tile
        keep_cnt = cls._connect_neighboring_tiles()
        cls.tiles = cls.tiles[keep_cnt]

        # connecting touching tiles with neighbor relation (see constructor)
        cls._update_neighbors_connections()

    @classmethod
    def _connect_neighboring_tiles(cls) -> np.ndarray:
        keep_contour = np.zeros(cls.tiles.shape, dtype=bool)
        tile: Self = None
        other_tile: Self = None

        for i, tile in enumerate(cls.tiles):
            for other_tile in cls.tiles[i + 1 :]:
                tile._connect_with_neigbor(  # pylint: disable=protected-access
                    other_tile
                )
            if tile.neighbors_count >= 1:
                keep_contour[i] = True
                cls._draw_circle(tile.center)
        return keep_contour

    @classmethod
    def _update_neighbors_connections(cls) -> None:
        tile: Self = None
        neighbor: Self = None

        for tile in cls.tiles:
            for neighbor_key, neighbor in tile.neighbors.items():
                if neighbor is not None:
                    if neighbor not in cls.tiles:
                        tile.neighbors[neighbor_key] = None
                        tile.neighbors_count -= 1
                    else:
                        cv2.line(cls._frame, tile.center, neighbor.center, (0, 0, 0), 1)

    @classmethod
    def get_tiles_contours(cls) -> np.ndarray:
        """Returns the contours of the tiles.

        Returns:
            np.ndarray: Contours of the tiles.
        """
        contours = np.ndarray((1, 4, 1, 2), dtype=int)
        tile: Self = None

        for tile in cls.tiles:
            contours = np.append(
                contours,
                [[[tile.vertexes[i]] for i in range(4)]],
                axis=0,
            )
        return contours[1:]

    def _connect_with_neigbor(self, poss_neighbor: Self):
        for i, vertex in enumerate(self.vertexes):
            for j, other_vertex in enumerate(poss_neighbor.vertexes):
                if self._are_vertices_connected(
                    vertex, other_vertex, i, j, poss_neighbor
                ):
                    self._create_neighbor_connection(poss_neighbor, i, j)

    def _are_vertices_connected(
        self,
        vertex: List[int],
        other_vertex: List[int],
        i: int,
        j: int,
        possible_neighbor: Self,
        jm = (j - 1) % 4
        ip = (i + 1) % 4

        return (vertex == other_vertex).all() and (
            self.vertexes[ip] == possible_neighbor.vertexes[jm]
        ).all()

    def _create_neighbor_connection(self, neighbor: Self, i: int, j: int) -> None:
        jm = (j - 1) % 4
        for key in self.NEIGHBORS_KEYS:
            index = int(key[1])

            self.neighbors[key] = neighbor if i == index else self.neighbors[key]
            neighbor.neighbors[key] = self if jm == index else neighbor.neighbors[key]

        self.neighbors_count += 1
        neighbor.neighbors_count += 1

    def set_indexes(self, x: int, y: int) -> None:
        """Sets the indexes of the tile on the board.

        Args:
            x (int): X index.
            y (int): Y index.
        """
        self.position = (x, y)

    def set_x_index(self, x: int) -> None:
        """Sets the x index of the tile on the board.

        Args:
            x (int): X index.
        """
        self.position = (x, self.position[1])

    def set_y_index(self, y: int) -> None:
        """Sets the y index of the tile on the board.

        Args:
            y (int): Y index.
        """
        self.position = (self.position[0], y)

    def get_dir_0_radians(self) -> Optional[float]:
        if self.neighbors["n01"] is None:
            return None

        return self.get_dir_2_point_rad(self.neighbors["n01"].center)

    @classmethod
    def get_frame(cls) -> Optional[np.ndarray]:
        """Returns the frame of the board.
        Frame is a copy of the original frame and can be used in OpenCV.

        Returns:
            Optional[np.ndarray]: Frame of the board.
        """
        return cls._frame.copy()

    def get_dir_2_point_rad(self, point: Optional[List[int]] = None) -> float:

        point = point if point is not None else [0, 0]
        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]

        adjustment = self._get_quadrant_in_rad(dx, dy)
        dx, dy = self._adujst_coordinates(dx, dy, adjustment[1])

        return self._calculate_angle(dx, dy, adjustment[0])

    def _get_quadrant_in_rad(self, dx: int, dy: int) -> Tuple[float, bool]:
        if dy < 0 <= dx:
            return HALF_PI, True
        if dx < 0 and dy < 0:
            return math.pi, False
        if dx < 0 <= dy:
            return 3 * HALF_PI, True

        return 0, False

    @staticmethod
    def _adujst_coordinates(dx: int, dy: int, should_swap: bool) -> Tuple[int, int]:
        if should_swap:
            dx, dy = dy, dx

        return abs(dx), abs(dy)

    @staticmethod
    def _calculate_angle(dx: int, dy: int, adjustment: float) -> float:

        angle = math.atan(dx / dy) if dy != 0 else HALF_PI
        return angle + adjustment

    def _is_point_in_rad_range(
        self, rad_min: float, rad_max: float, point: Optional[List[int]] = None
    ):
        if point is None:
            point = [0, 0]

        dir_tmp = self.get_dir_2_point_rad(point)

        return (
            (rad_min <= dir_tmp <= rad_max)
            or (dir_tmp <= rad_max < rad_min)
            or (rad_max < rad_min <= dir_tmp)
        )

    def get_neighbor_in_rad_range(
        self, rad_min: float, rad_max: float
    ) -> Optional[Self]:


        return next(
            (
                n
                for n in self.neighbors.values()
                if n is not None
                and self._is_point_in_rad_range(rad_min, rad_max, n.center)
            ),
            None,
        )

        Args:
            dir_rad (_type_): Radial direction.
            dir_idx (_type_): Index of the direction.

        Returns:
            int: Number of steps in given direction.
        """

        # if was checked already - returning 0
        if self.was_checked_in_dir_idx[dir_idx]:
            return 0

        # flagging self as checked already in dir_idx
        self.was_checked_in_dir_idx[dir_idx] = True

        # getting the neighbor in the direction
        direction_ranges = self._calculate_direction_ranges(dir_rad)
        neighbor_steps = self._get_neighbor_steps(direction_ranges, dir_rad, dir_idx)

        return max(neighbor_steps, default=0)

    def _calculate_direction_ranges(self, dir_rad: float) -> Dict[str, float]:
        ranges = {
            "minus_min": self._normalize_angle(dir_rad - THREE_QUARTER_PI),
            "minus_max": self._normalize_angle(dir_rad - QUARTER_PI),
            "plus_min": self._normalize_angle(dir_rad + QUARTER_PI),
            "plus_max": self._normalize_angle(dir_rad + THREE_QUARTER_PI),
        }
        return ranges

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        if angle < 0:
            return angle + TWO_PI
        if angle >= TWO_PI:
            return angle - TWO_PI

        return angle

    def _get_neighbor_steps(
        self, ranges: Dict[str, float], dir_rad: float, dir_idx: int
    ) -> List[int]:
        results = []
        same_dir = self.get_neighbor_in_rad_range(
            ranges["minus_max"], ranges["plus_min"]
        )

        if same_dir is not None:
            # one more because it is in checked direction
            results.append(same_dir.get_num_of_steps_in_dir_rad(dir_rad, dir_idx) + 1)

        for min_range, max_range in (ranges["minus_min"], ranges["minus_max"]), (
            ranges["plus_min"],
            ranges["plus_max"],
        ):
            side_neighbor = self.get_neighbor_in_rad_range(min_range, max_range)
            if side_neighbor is not None:
                results.append(
                    side_neighbor.get_num_of_steps_in_dir_rad(dir_rad, dir_idx)
                )

        return results

    def index_neighbors(self, dir_0: float) -> None:

            return

        dir_01 = self._normalize_angle(dir_0 + QUARTER_PI)
        dir_12 = self._normalize_angle(dir_01 + HALF_PI)
        dir_23 = self._normalize_angle(dir_12 + HALF_PI)
        dir_30 = self._normalize_angle(dir_23 + HALF_PI)

        neighbors_data = [
            (self.get_neighbor_in_rad_range(dir_30, dir_01), (0, -1)),
            (self.get_neighbor_in_rad_range(dir_01, dir_12), (1, 0)),
            (self.get_neighbor_in_rad_range(dir_12, dir_23), (0, 1)),
            (self.get_neighbor_in_rad_range(dir_23, dir_30), (-1, 0)),
        ]

        for neighbor, (dx, dy) in neighbors_data:
            if neighbor and (None in neighbor.position):
                neighbor.set_indexes(self.position[0] + dx, self.position[1] + dy)
                neighbor.index_neighbors(dir_0)

    def get_vertex_in_rad_range(
        self, rad_min: float, rad_max: float
    ) -> Optional[List[int]]:




if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    processor = ContourProcessor()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        image_contours = processor.get_contours(frame)
        BoardTile.create_tiles(frame, image_contours)

        display_image = BoardTile.get_frame()
        cv2.drawContours(display_image, image_contours, -1, (0, 255, 0), 2)
        cv2.imshow("frame", display_image)

        if cv2.waitKey(0) & 0xFF == ord("q"):
            break
