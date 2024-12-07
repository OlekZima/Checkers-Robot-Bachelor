"""Module for representing a tile on the board for the cv2 processing."""

import math
from typing import ClassVar, List, Optional, Self

import cv2
import numpy as np
from src.common.utilities import (
    HALF_PI,
    THREE_QUARTER_PI,
    get_avg_pos,
    TWO_PI,
    QUARTER_PI,
)

from .contours_recognition import ContourProcessor


class BoardTile:
    tiles: ClassVar[np.ndarray[Self]] = np.array([])
    frame: ClassVar[Optional[np.ndarray]] = None

    def __init__(self, points: Optional[List[List[int]]] = None) -> None:
        # theese will be used to see relation with other tiles
        # and get the final position of the board
        if points is not None:
            self.vertexes = points
        else:
            self.vertexes = [[0, 0] for _ in range(4)]

        self.center = get_avg_pos(points)
        # print (self.vertexes)

        # neighbouring tiles - theese will be assigned later to map the board
        #
        # neighbour n01 means that the neighbour share vertexes[0] and vertexes[1] points
        # with this tile

        self.neighbors = {
            "n01": None,
            "n12": None,
            "n23": None,
            "n30": None,
        }
        self.neighbors_count = 0  # will be updated when neighbours are assigned

        self.x_idx = None
        self.y_idx = None  # Position on checkers board
        self.was_checked_in_dir_idx = [False, False, False, False]

    @classmethod
    def create_tiles(cls, image: np.ndarray, contours: np.ndarray) -> None:
        BoardTile.frame = image
        # contours.shape == ( -1, 4, 1, 2)

        # STEP 0 - creating tiles from all contours
        # RESET - removing all previous tiles
        BoardTile.tiles = np.array([])
        for cnt in contours:
            BoardTile.tiles = np.append(
                BoardTile.tiles,
                BoardTile(points=[cnt[0][0], cnt[1][0], cnt[2][0], cnt[3][0]]),
            )

        # STEP 1 - only keepeing tiles that have at least 1 neighbors_count
        # - so that we only get our board tiles and not disconected false readings
        #
        # ALSO - connecting touching tiles with neighbour relation (see constructor)
        keep_cnt = np.zeros(BoardTile.tiles.shape, dtype=bool)
        for i, cnt1 in enumerate(BoardTile.tiles):
            for cntn in BoardTile.tiles[i + 1 :]:
                cnt1.assign_if_neighbour(cntn)

            if cnt1.neighbors_count >= 1:  # Finally 1 works well
                keep_cnt[i] = True
                cv2.circle(BoardTile.frame, cnt1.center, 3, (0, 0, 255), 1)
                # print(cnt1.neighbors_count)
        # Keeping only tiles with at least 2 neighbours
        BoardTile.tiles = BoardTile.tiles[keep_cnt]

        for tile in BoardTile.tiles:
            if tile.neighbors["n01"] is not None:
                if tile.neighbors["n01"] not in BoardTile.tiles:
                    tile.neighbors["n01"] = None
                    tile.neighbors_count -= 1
                else:
                    cv2.line(
                        BoardTile.frame,
                        tile.center,
                        tile.neighbors["n01"].center,
                        (0, 0, 0),
                        1,
                    )
            if tile.neighbors["n12"] is not None:
                if tile.neighbors["n12"] not in BoardTile.tiles:
                    tile.neighbors["n12"] = None
                    tile.neighbors_count -= 1
                else:
                    cv2.line(
                        BoardTile.frame,
                        tile.center,
                        tile.neighbors["n12"].center,
                        (0, 0, 0),
                        1,
                    )
            if tile.neighbors["n23"] is not None:
                if tile.neighbors["n23"] not in BoardTile.tiles:
                    tile.neighbors["n23"] = None
                    tile.neighbors_count -= 1
                else:
                    cv2.line(
                        BoardTile.frame,
                        tile.center,
                        tile.neighbors["n23"].center,
                        (0, 0, 0),
                        1,
                    )
            if tile.neighbors["n30"] is not None:
                if tile.neighbors["n30"] not in BoardTile.tiles:
                    tile.neighbors["n30"] = None
                    tile.neighbors_count -= 1
                else:
                    cv2.line(
                        BoardTile.frame,
                        tile.center,
                        tile.neighbors["n30"].center,
                        (0, 0, 0),
                        1,
                    )
            cv2.putText(
                BoardTile.frame,
                f"{tile.neighbors_count}",
                tile.center,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (0, 255, 0),
                1,
                cv2.LINE_AA,
            )

    @classmethod
    def get_tiles_contours(cls):
        contours = np.ndarray((1, 4, 1, 2), dtype=int)
        for tile in cls.tiles:
            contours = np.append(
                contours,
                [[[tile.vertexes[i]] for i in range(4)]],
                axis=0,
            )
        return contours[1:]

    def assign_if_neighbour(self, poss_neighbour: Self):
        for i, vertex in enumerate(self.vertexes):
            for j, other_vertex in enumerate(poss_neighbour.vertexes):
                if (vertex == other_vertex).all():
                    # jp = (j + 1) % 4
                    jm = (j - 1) % 4
                    ip = (i + 1) % 4

                    # if (self.vertexes[ip] == poss_neighbour.vertexes[jp]).all():
                    #     indices = ["n01", "n12", "n23", "n30"]
                    #     for indice in indices:
                    #         self.neighbors[indice] = (
                    #             poss_neighbour
                    #             if i == int(indice[1])
                    #             else self.neighbors[indice]
                    #         )
                    #         poss_neighbour.neighbors[indice] = (
                    #             self
                    #             if j == int(indice[1])
                    #             else poss_neighbour.neighbors[indice]
                    #         )

                    #     self.neighbors_count += 1
                    #     poss_neighbour.neighbors_count += 1

                    #     return True
                    if (self.vertexes[ip] == poss_neighbour.vertexes[jm]).all():
                        indices = ["n01", "n12", "n23", "n30"]
                        for indice in indices:
                            self.neighbors[indice] = (
                                poss_neighbour
                                if i == int(indice[1])
                                else self.neighbors[indice]
                            )
                            poss_neighbour.neighbors[indice] = (
                                self
                                if jm == int(indice[1])
                                else poss_neighbour.neighbors[indice]
                            )

                        self.neighbors_count += 1
                        poss_neighbour.neighbors_count += 1

                        return True
        return False

    def assign_indexes(self, x: int, y: int) -> None:
        self.x_idx, self.y_idx = x, y

    def assign_x_idx(self, x_idx) -> None:
        self.x_idx = x_idx

    def assign_y_idx(self, y_idx) -> None:
        self.y_idx = y_idx

    def get_dir_0_radians(self) -> Optional[float]:
        if self.neighbors["n01"] is None:
            return None

        return self.get_dir_2_point_rad(self.neighbors["n01"].center)

    def get_dir_2_point_rad(self, point: Optional[List[int]] = None) -> float:
        if point is None:
            point = [0, 0]

        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]
        # print(f'''Jestem sprawdzaczem kierunku do punktu
        # Ta kostka {self.center}, cel {point}
        # dx = {dx}, dy = {dy}''')
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

    def is_point_in_rad_range(
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

    def get_neighbour_in_rad_range(self, rad_min, rad_max) -> Optional[Self]:
        for n in self.neighbors.values():
            if n is not None and self.is_point_in_rad_range(rad_min, rad_max, n.center):
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
        same_dir = self.get_neighbour_in_rad_range(dir_minus_max, dir_plus_min)
        if same_dir is not None:
            results.append(
                same_dir.get_num_of_steps_in_dir_rad(dir_rad, dir_idx) + 1
            )  # one more because it is in checked direction

        dir_minus = self.get_neighbour_in_rad_range(dir_minus_min, dir_minus_max)
        if dir_minus is not None:
            results.append(dir_minus.get_num_of_steps_in_dir_rad(dir_rad, dir_idx))
        dir_plus = self.get_neighbour_in_rad_range(dir_plus_min, dir_plus_max)
        if dir_plus is not None:
            results.append(dir_plus.get_num_of_steps_in_dir_rad(dir_rad, dir_idx))
        # retrieving data of max num of steps in dir
        max_num_of_steps = max(results, default=0)

        return max_num_of_steps

    def index_neighbours(self, dir_0) -> None:
        if self.x_idx is None or self.y_idx is None:
            return

        cv2.putText(
            BoardTile.frame,
            f"{self.x_idx},{self.y_idx}",
            [self.center[0] - 5, self.center[1]],
            cv2.FONT_HERSHEY_SIMPLEX,
            0.3,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

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
        dir_0_n = self.get_neighbour_in_rad_range(dir_30, dir_01)
        dir_1_n = self.get_neighbour_in_rad_range(dir_01, dir_12)
        dir_2_n = self.get_neighbour_in_rad_range(dir_12, dir_23)
        dir_3_n = self.get_neighbour_in_rad_range(dir_23, dir_30)
        if dir_0_n is not None:
            if dir_0_n.x_idx is None or dir_0_n.y_idx is None:
                dir_0_n.assign_indexes(self.x_idx, self.y_idx - 1)
                dir_0_n.index_neighbours(dir_0)
        if dir_1_n is not None:
            if dir_1_n.x_idx is None or dir_1_n.y_idx is None:
                dir_1_n.assign_indexes(self.x_idx + 1, self.y_idx)
                dir_1_n.index_neighbours(dir_0)

        if dir_2_n is not None:
            if dir_2_n.x_idx is None or dir_2_n.y_idx is None:
                dir_2_n.assign_indexes(self.x_idx, self.y_idx + 1)
                dir_2_n.index_neighbours(dir_0)

        if dir_3_n is not None:
            if dir_3_n.x_idx is None or dir_3_n.y_idx is None:
                dir_3_n.assign_indexes(self.x_idx - 1, self.y_idx)
                dir_3_n.index_neighbours(dir_0)

    def get_vertex_in_rad_range(self, rad_min, rad_max):
        for v in self.vertexes:
            if self.is_point_in_rad_range(rad_min, rad_max, v):
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

        display_image = BoardTile.frame.copy()
        cv2.drawContours(display_image, image_contours, -1, (0, 255, 0), 2)
        cv2.imshow("frame", display_image)

        if cv2.waitKey(0) & 0xFF == ord("q"):
            break
