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
                tile._connect_with_neigbor(other_tile)  # pylint: disable=protected-access

            if tile.neighbors_count >= 1:
                keep_contour[i] = True
                cv2.circle(BoardTile._frame, tile.center, 3, (0, 0, 255), 1)
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
    ):
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
        if point is None:
            point = [0, 0]

        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]

        dpi = 0
        if dy < 0 <= dx:
            dpi = HALF_PI
            dx, dy = dy, dx
        elif dx < 0 and dy < 0:
            dpi = math.pi
        elif dx < 0 <= dy:
            dpi = 3 * HALF_PI
            dx, dy = dy, dx

        dx = math.fabs(dx)
        dy = math.fabs(dy)

        # if dy != 0:
        #     res = math.atan(float(dx) / float(dy))
        #     res += dpi
        #     # print(f'Obliczyłem: {res}')
        #     return res
        # else:
        #     res = HALF_PI
        #     res += dpi
        #     # print(f'Obliczyłem: {res}')
        #     return res
        res = math.atan(dx / dy) if dy != 0 else HALF_PI
        res += dpi

        return res

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

    def get_neighbor_in_rad_range(self, rad_min, rad_max) -> Optional[Self]:
        for n in self.neighbors.values():
            if n is not None and self._is_point_in_rad_range(
                rad_min, rad_max, n.center
            ):
                return n

        return None

    def get_num_of_steps_in_dir_rad(self, dir_rad, dir_idx) -> int:
        """Recursively counts number of steps in given direction.

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

        # determining border between dirs
        dir_minus_min = dir_rad - THREE_QUARTER_PI
        if dir_minus_min < 0:
            dir_minus_min += TWO_PI
        dir_minus_max = dir_rad - QUARTER_PI
        if dir_minus_max < 0:
            dir_minus_max += TWO_PI
        dir_plus_min = dir_rad + QUARTER_PI
        if dir_plus_min >= TWO_PI:
            dir_plus_min -= TWO_PI
        dir_plus_max = dir_rad + THREE_QUARTER_PI
        if dir_plus_max >= TWO_PI:
            dir_plus_max -= TWO_PI
        # calling this func recursively for possibly 3 next tiles and gathering readings
        results = []
        same_dir = self.get_neighbor_in_rad_range(dir_minus_max, dir_plus_min)
        if same_dir is not None:
            # one more because it is in checked direction
            results.append(same_dir.get_num_of_steps_in_dir_rad(dir_rad, dir_idx) + 1)

        dir_minus = self.get_neighbor_in_rad_range(dir_minus_min, dir_minus_max)
        if dir_minus is not None:
            results.append(dir_minus.get_num_of_steps_in_dir_rad(dir_rad, dir_idx))
        dir_plus = self.get_neighbor_in_rad_range(dir_plus_min, dir_plus_max)
        if dir_plus is not None:
            results.append(dir_plus.get_num_of_steps_in_dir_rad(dir_rad, dir_idx))

        # retrieving data of max num of steps in dir
        max_num_of_steps = max(results, default=0)

        return max_num_of_steps

    def index_neighbors(self, dir_0) -> None:
        if self.position[0] is None or self.position[1] is None:
            return

        # cv2.putText(
        #     BoardTile.frame,
        #     f"{self.position[0]},{self.position[1]}",
        #     [self.center[0] - 5, self.center[1]],
        #     cv2.FONT_HERSHEY_SIMPLEX,
        #     0.3,
        #     (0, 255, 0),
        #     1,
        #     cv2.LINE_AA,
        # )

        dir_01 = dir_0 + QUARTER_PI
        if dir_01 >= TWO_PI:
            dir_01 -= TWO_PI

        dir_12 = dir_01 + HALF_PI
        if dir_12 >= TWO_PI:
            dir_12 -= TWO_PI
        dir_23 = dir_12 + HALF_PI
        if dir_23 >= TWO_PI:
            dir_23 -= TWO_PI
        dir_30 = dir_23 + HALF_PI
        if dir_30 >= TWO_PI:
            dir_30 -= TWO_PI
        dir_0_n = self.get_neighbor_in_rad_range(dir_30, dir_01)
        dir_1_n = self.get_neighbor_in_rad_range(dir_01, dir_12)
        dir_2_n = self.get_neighbor_in_rad_range(dir_12, dir_23)
        dir_3_n = self.get_neighbor_in_rad_range(dir_23, dir_30)
        if dir_0_n is not None:
            if dir_0_n.position[0] is None or dir_0_n.position[1] is None:
                dir_0_n.set_indexes(self.position[0], self.position[1] - 1)
                dir_0_n.index_neighbors(dir_0)
        if dir_1_n is not None:
            if dir_1_n.position[0] is None or dir_1_n.position[1] is None:
                dir_1_n.set_indexes(self.position[0] + 1, self.position[1])
                dir_1_n.index_neighbors(dir_0)

        if dir_2_n is not None:
            if dir_2_n.position[0] is None or dir_2_n.position[1] is None:
                dir_2_n.set_indexes(self.position[0], self.position[1] + 1)
                dir_2_n.index_neighbors(dir_0)

        if dir_3_n is not None:
            if dir_3_n.position[0] is None or dir_3_n.position[1] is None:
                dir_3_n.set_indexes(self.position[0] - 1, self.position[1])
                dir_3_n.index_neighbors(dir_0)

    def get_vertex_in_rad_range(self, rad_min, rad_max):
        for v in self.vertexes:
            if self._is_point_in_rad_range(rad_min, rad_max, v):
                return v
        return None


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
