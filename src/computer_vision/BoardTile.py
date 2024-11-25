from src.checkers_game_and_decisions.utilities import get_avg_pos


import cv2
import numpy as np


import math


class BoardTile:
    tiles = []  # storing all board tiles
    frame = None

    @classmethod
    def create_tiles(cls, img, contours):
        BoardTile.frame = img

        # contours.shape == ( -1, 4, 1, 2)

        # RESET - removing all previous tiles
        BoardTile.tiles = []

        # STEP 0 - creating tiles from all contours
        for cnt in contours:
            BoardTile.tiles.append(
                BoardTile(points=[cnt[0][0], cnt[1][0], cnt[2][0], cnt[3][0]])
            )

        BoardTile.tiles = np.array(BoardTile.tiles, dtype=BoardTile)

        # STEP 1 - only keepeing tiles that have at least 1 n_of_neighbours
        # - so that we only get our board tiles and not disconected false readings
        #
        # ALSO - connecting touching tiles with neighbour relation (see constructor)
        keep_cnt = np.zeros(BoardTile.tiles.shape, dtype=bool)

        for i, cnt1 in enumerate(BoardTile.tiles):
            for cntn in BoardTile.tiles[i + 1 :]:
                cnt1.assign_if_neighbour(cntn)

            if cnt1.n_of_neighbours >= 1:  # Finally 1 works well
                keep_cnt[i] = True
                cv2.circle(BoardTile.frame, cnt1.center, 3, (0, 0, 255), 1)
                # print(cnt1.n_of_neighbours)

        BoardTile.tiles = BoardTile.tiles[
            keep_cnt
        ]  # Keeping only tiles with at least 2 neighbours

        for tile in BoardTile.tiles:
            if tile.n01 is not None:
                if tile.n01 not in BoardTile.tiles:
                    tile.n01 = None
                    tile.n_of_neighbours -= 1
                else:
                    cv2.line(BoardTile.frame, tile.center, tile.n01.center, (0, 0, 0), 1)
            if tile.n12 is not None:
                if tile.n12 not in BoardTile.tiles:
                    tile.n12 = None
                    tile.n_of_neighbours -= 1
                else:
                    pass  # cv.line(BoardTile.frame, tile.center, tile.n12.center, (0,0,0), 1)
            if tile.n23 is not None:
                if tile.n23 not in BoardTile.tiles:
                    tile.n23 = None
                    tile.n_of_neighbours -= 1
                else:
                    pass  # cv.line(BoardTile.frame, tile.center, tile.n23.center, (0,0,0), 1)
            if tile.n30 is not None:
                if tile.n30 not in BoardTile.tiles:
                    tile.n30 = None
                    tile.n_of_neighbours -= 1
                else:
                    cv2.line(BoardTile.frame, tile.center, tile.n30.center, (0, 0, 0), 1)
            # cv.putText(BoardTile.frame, f'{tile.n_of_neighbours}', tile.center, cv.FONT_HERSHEY_SIMPLEX, 0.35, (0,255,0), 1, cv.LINE_AA)

    @classmethod
    def get_tiles_contours(cls):
        contours = np.ndarray((1, 4, 1, 2), dtype=int)
        for t in BoardTile.tiles:
            contours = np.append(
                contours,
                [[[t.vertexes[0]], [t.vertexes[1]], [t.vertexes[2]], [t.vertexes[3]]]],
                axis=0,
            )
        return contours[1:]

    def __init__(self, points=[[0, 0], [0, 0], [0, 0], [0, 0]]):
        # theese will be used to see relation with other tiles
        # and get the final position of the board
        self.vertexes = points
        self.center = get_avg_pos(points)
        # print (self.vertexes)

        # neighbouring tiles - theese will be assigned later to map the board
        #
        # neighbour n01 means that the neighbour share vertexes[0] and vertexes[1] points
        # with this tile
        self.n01 = None
        self.n12 = None
        self.n23 = None
        self.n30 = None
        self.n_of_neighbours = 0  # will be updated when neighbours are assigned

        # ilustration showing direction naming convention and indexing algorithm:
        # https://drive.google.com/file/d/1BF7BsXUdXmlOtog8Z4uC_gXMGwE0EBmd/view?usp=sharing
        self.x_idx = None
        self.y_idx = None  # Position on checkers board

        self.was_checked_in_dir_idx = [False, False, False, False]

    def assign_if_neighbour(self, poss_neighbour):
        for i, _ in enumerate(self.vertexes):
            for j, _ in enumerate(poss_neighbour.vertexes):
                if (self.vertexes[i] == poss_neighbour.vertexes[j]).all():
                    jp = 0 if j + 1 == len(poss_neighbour.vertexes) else j + 1
                    jm = len(poss_neighbour.vertexes) - 1 if j - 1 == -1 else j - 1
                    ip = 0 if i + 1 == len(poss_neighbour.vertexes) else i + 1

                    if (self.vertexes[ip] == poss_neighbour.vertexes[jp]).all():
                        self.n01 = (
                            poss_neighbour if i == 0 else self.n01
                        )  # agrhhh awful
                        self.n12 = poss_neighbour if i == 1 else self.n12
                        self.n23 = poss_neighbour if i == 2 else self.n23
                        self.n30 = poss_neighbour if i == 3 else self.n30
                        self.n_of_neighbours += 1
                        poss_neighbour.n01 = (
                            self if j == 0 else poss_neighbour.n01
                        )  # agrhhh awful
                        poss_neighbour.n12 = self if j == 1 else poss_neighbour.n12
                        poss_neighbour.n23 = self if j == 2 else poss_neighbour.n23
                        poss_neighbour.n30 = self if j == 3 else poss_neighbour.n30
                        poss_neighbour.n_of_neighbours += 1
                        # print(f'{self.vertexes}\n{poss_neighbour.vertexes}')
                        return True

                    if (self.vertexes[ip] == poss_neighbour.vertexes[jm]).all():
                        self.n01 = (
                            poss_neighbour if i == 0 else self.n01
                        )  # agrhhh awful
                        self.n12 = poss_neighbour if i == 1 else self.n12
                        self.n23 = poss_neighbour if i == 2 else self.n23
                        self.n30 = poss_neighbour if i == 3 else self.n30
                        self.n_of_neighbours += 1
                        poss_neighbour.n01 = (
                            self if jm == 0 else poss_neighbour.n01
                        )  # agrhhh awful
                        poss_neighbour.n12 = self if jm == 1 else poss_neighbour.n12
                        poss_neighbour.n23 = self if jm == 2 else poss_neighbour.n23
                        poss_neighbour.n30 = self if jm == 3 else poss_neighbour.n30
                        poss_neighbour.n_of_neighbours += 1
                        # print(f'{self.vertexes}\n{poss_neighbour.vertexes}')
                        return True

        return False

    def assign_indexes(self, id_x, id_y):
        self.x_idx = id_x
        self.y_idx = id_y

    def assign_x_idx(self, x_idx):
        self.x_idx = x_idx

    def assign_y_idx(self, y_idx):
        self.y_idx = y_idx

    def get_dir_0_radians(self):
        if self.n01 is None:
            return None

        return self.get_dir_2_point_rad(self.n01.center)

    def get_dir_2_point_rad(self, point=[0, 0]):
        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]

        # print(f'''Jestem sprawdzaczem kierunku do punktu
        # Ta kostka {self.center}, cel {point}
        # dx = {dx}, dy = {dy}''')

        dpi = 0

        if dx >= 0 and dy < 0:
            dpi = math.pi / 2.0
            tmp = dx
            dx = dy
            dy = tmp
        elif dx < 0 and dy < 0:
            dpi = math.pi
        elif dx < 0 and dy >= 0:
            dpi = 3 * math.pi / 2.0
            tmp = dx
            dx = dy
            dy = tmp

        dx = math.fabs(dx)
        dy = math.fabs(dy)

        if dy != 0:
            res = math.atan(float(dx) / float(dy))
            res += dpi

            # print(f'Obliczyłem: {res}')
            return res
        else:
            res = math.pi / 2.0
            res += dpi
            # print(f'Obliczyłem: {res}')

            return res

    def is_point_in_rad_range(self, rad_min, rad_max, point=[0, 0]):
        dir_tmp = self.get_dir_2_point_rad(point)
        # print(f'''Sprawdzam, czy podany punkt jest w zakresie
        # Dostałem: rad_min = {rad_min}, rad_max = {rad_max}
        # Obliczyłem, że kierunek do punktu to {dir_tmp}''')
        if (
            (rad_min <= rad_max and dir_tmp >= rad_min and dir_tmp <= rad_max)
            or (rad_min > rad_max and dir_tmp <= rad_max)
            or (rad_min > rad_max and dir_tmp >= rad_min)
        ):
            # print('Mój werdykt - TRUE')
            return True
        # print('Mój werdykt - FALSE')
        return False

    def get_neighbour_in_rad_range(self, rad_min, rad_max):
        if self.n01 is not None:
            if self.is_point_in_rad_range(rad_min, rad_max, self.n01.center):
                return self.n01
        if self.n12 is not None:
            if self.is_point_in_rad_range(rad_min, rad_max, self.n12.center):
                return self.n12
        if self.n23 is not None:
            if self.is_point_in_rad_range(rad_min, rad_max, self.n23.center):
                return self.n23
        if self.n30 is not None:
            if self.is_point_in_rad_range(rad_min, rad_max, self.n30.center):
                return self.n30

        return None

    def get_num_of_steps_in_dir_rad(
        self, dir_rad, dir_idx
    ):  # recursive function for indexing steps
        # if was checked already - returning 0
        if self.was_checked_in_dir_idx[dir_idx]:
            return 0

        # flagging self as checked already in dir_idx
        self.was_checked_in_dir_idx[dir_idx] = True

        # determining border between dirs
        dir_minus_min = dir_rad - math.pi * 3.0 / 4.0
        if dir_minus_min < 0:
            dir_minus_min += math.pi * 2.0

        dir_minus_max = dir_rad - math.pi / 4.0
        if dir_minus_max < 0:
            dir_minus_max += math.pi * 2.0

        dir_plus_min = dir_rad + math.pi / 4.0
        if dir_plus_min >= math.pi * 2.0:
            dir_plus_min -= math.pi * 2.0

        dir_plus_max = dir_rad + math.pi * 3.0 / 4.0
        if dir_plus_max >= math.pi * 2.0:
            dir_plus_max -= math.pi * 2.0

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
        max_num_of_steps = max(results)
        for_max = 0
        for res in results:
            if res > for_max:
                for_max = res

        assert max_num_of_steps == for_max

        return max_num_of_steps

    def index_neighbours(self, dir_0):
        if self.x_idx is None or self.y_idx is None:
            return -1
        else:
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

        dir_01 = dir_0 + math.pi / 4.0
        if dir_01 >= math.pi * 2.0:
            dir_01 -= math.pi * 2.0

        dir_12 = dir_01 + math.pi / 2.0
        if dir_12 >= math.pi * 2.0:
            dir_12 -= math.pi * 2.0

        dir_23 = dir_12 + math.pi / 2.0
        if dir_23 >= math.pi * 2.0:
            dir_23 -= math.pi * 2.0

        dir_30 = dir_23 + math.pi / 2.0
        if dir_30 >= math.pi * 2.0:
            dir_30 -= math.pi * 2.0

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

        return 0

    def get_vertex_in_rad_range(self, rad_min, rad_max):
        for v in self.vertexes:
            if self.is_point_in_rad_range(rad_min, rad_max, v):
                return v
        return None
