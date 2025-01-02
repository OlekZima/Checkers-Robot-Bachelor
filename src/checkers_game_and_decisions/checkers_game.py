from copy import deepcopy
from typing import List, Optional

import numpy as np

from src.common.enum_entities import Color, Status
from src.common.exceptions import (
    CheckersGameEndError,
    CheckersGameNotPermittedMoveError,
)
from src.common.utilities import (
    get_coord_from_tile_id,
    get_tile_id_from_coord,
)


# Class contains basic info about game - model:
#   -> state of the board
#   -> log of movements
#   -> points collected per each side
#   -> info which player turn it is
#
# It has methods to:
#   -> get previously described values
#   -> check if game is won/draw at current point
#   -> return all movements possible
#   -> perform a specific movement by player, whose turn it is
# These methods can be based on class methods which take game state as a parameter - as we may need it later
# for decision making algorithm
class CheckersGame:
    def __init__(self):
        # The convention is that:
        #   - color wise:
        #       -ORANGE -> 1 is man, 2 is king
        #       -BLUE (in normal gameplay it is WHITE) -> -1 is man, -2 is king
        #       -0 is an empty tile
        #   - game state is 2d matrix:
        #       - it is to be perceived as list of columns
        #       - the orange are on the upper side
        #       - the game_state[0][0] is the upper left tile
        #       - the game_state[7][7] is the bottom right tile
        #       - the upper side is y = 0
        #       - the bottom side is y = 7
        self.game_state: np.ndarray = np.array(
            [
                [0, 1, 0, 0, 0, -1, 0, -1],
                [1, 0, 1, 0, 0, 0, -1, 0],
                [0, 1, 0, 0, 0, -1, 0, -1],
                [1, 0, 1, 0, 0, 0, -1, 0],
                [0, 1, 0, 0, 0, -1, 0, -1],
                [1, 0, 1, 0, 0, 0, -1, 0],
                [0, 1, 0, 0, 0, -1, 0, -1],
                [1, 0, 1, 0, 0, 0, -1, 0],
            ]
        )

        # First move always goes to BLUE (in normal gameplay - white)
        self.turn_of: Color = Color.BLUE

        self.turn_player_opts = CheckersGame.get_color_poss_opts(
            self.turn_of, self.game_state
        )

        # log of gameplay is saved as list of lists (each 'smaller' list is of integers - each represents id of tile - see rules_desc)
        # each one round movement is a list of integers:
        #   -> first item is starting id of a moved piece
        #   -> each positive integer then is id of next tile the piece landed on
        #   -> each negative integer indicates id of tile that the opponent piece was jumped over
        #   -> for single move - the list has two items (both positive)
        #   -> for jumping sequence -> the list has odd number of items and goes [+, -, ... , +]
        self.log = []

        # will be a list of tuples, where tuple[0] is player having turn, and tuple [1] is game_state
        self.draw_criteria_log = [(self.turn_of, self.get_game_state())]

        self.orange_score = 0
        self.blue_score = 0

        self.status = Status.IN_PROGRESS

        # will be filled with Color.ORANGE/Color.BLUE if state becomes Status.WON
        self.winning_player = None

    @classmethod
    def _get_value_of_tile(cls, tile_id: int, game_state: np.ndarray) -> int:
        x, y = get_coord_from_tile_id(tile_id)

        return game_state[x][y]

    @classmethod
    def _get_man_poss_moves(cls, tile_id: int, game_state: np.ndarray):
        poss_moves = []
        val_of_id = CheckersGame._get_value_of_tile(tile_id, game_state)

        # this tile doesn't contain a man piece of either player
        if val_of_id not in (-1, 1):
            return None

        x, y = get_coord_from_tile_id(tile_id)

        # ORANGE -> moves 'down' towards bigger ids
        if val_of_id == 1:
            # piece should have been crowned and was mistakenly treated as man
            if y + 1 == 8:
                return None

            if x - 1 >= 0 and game_state[x - 1][y + 1] == 0:
                poss_moves.append([tile_id, get_tile_id_from_coord(x - 1, y + 1)])
            if x + 1 < 8 and game_state[x + 1][y + 1] == 0:
                poss_moves.append([tile_id, get_tile_id_from_coord(x + 1, y + 1)])

        # BLUE -> moves 'up' towards lower ids
        else:
            # piece should have been crowned and was mistakenly treated as man
            if y == 0:
                return None

            if x - 1 >= 0 and game_state[x - 1][y - 1] == 0:
                poss_moves.append([tile_id, get_tile_id_from_coord(x - 1, y - 1)])
            if x + 1 < 8 and game_state[x + 1][y - 1] == 0:
                poss_moves.append([tile_id, get_tile_id_from_coord(x + 1, y - 1)])

        return poss_moves

    @classmethod
    def _get_king_poss_moves(cls, tile_id: int, game_state: np.ndarray):
        poss_moves = []
        val_of_id = CheckersGame._get_value_of_tile(tile_id, game_state)

        # this tile doesn't contain a king piece of either player
        if val_of_id not in (-2, 2):
            return None

        x, y = get_coord_from_tile_id(tile_id)

        # Diagonal of increasing x and y
        x_tmp = x + 1
        y_tmp = y + 1
        while x_tmp < 8 and y_tmp < 8 and game_state[x_tmp][y_tmp] == 0:
            poss_moves.append([tile_id, get_tile_id_from_coord(x_tmp, y_tmp)])
            x_tmp += 1
            y_tmp += 1

        # Diagonal of decreasing x and increasing y
        x_tmp = x - 1
        y_tmp = y + 1
        while x_tmp >= 0 and y_tmp < 8 and game_state[x_tmp][y_tmp] == 0:
            poss_moves.append([tile_id, get_tile_id_from_coord(x_tmp, y_tmp)])
            x_tmp -= 1
            y_tmp += 1

        # Diagonal of decreasing x and y
        x_tmp = x - 1
        y_tmp = y - 1
        while x_tmp >= 0 and y_tmp >= 0 and game_state[x_tmp][y_tmp] == 0:
            poss_moves.append([tile_id, get_tile_id_from_coord(x_tmp, y_tmp)])
            x_tmp -= 1
            y_tmp -= 1

        # Diagonal of increasing x and decreasing y
        x_tmp = x + 1
        y_tmp = y - 1
        while x_tmp < 8 and y_tmp >= 0 and game_state[x_tmp][y_tmp] == 0:
            poss_moves.append([tile_id, get_tile_id_from_coord(x_tmp, y_tmp)])
            x_tmp += 1
            y_tmp -= 1

        return poss_moves

    @classmethod
    def _get_man_poss_jumps(cls, tile_id, game_state, prev_seq=None):
        if prev_seq is None:
            prev_seq = []
        poss_jumps = []
        val_of_id = CheckersGame._get_value_of_tile(tile_id, game_state)

        # this tile doesn't contain a man piece of either player
        if val_of_id not in (-1, 1):
            return None

        x, y = get_coord_from_tile_id(tile_id)

        if len(prev_seq) == 0:
            x_curr = x
            y_curr = y
        else:
            x_curr, y_curr = get_coord_from_tile_id(prev_seq[len(prev_seq) - 1])

        # Looking for jumps on diagonal - increasing x and y
        if (
            # we need to move two tiles for jump
            x_curr + 2 < 8
            # we need to move two tiles for jump
            and y_curr + 2 < 8
            # we cannot jump two times over same opponent piece
            and ((-1) * get_tile_id_from_coord(x_curr + 1, y_curr + 1)) not in prev_seq
            # so that we have opposing side pieces
            and game_state[x][y] * game_state[x_curr + 1][y_curr + 1] < 0
            # we have empty tile after opponent (or the tile was initial jumping piece tile)
            and (
                game_state[x_curr + 2][y_curr + 2] == 0
                or (x_curr + 2 == x and y_curr + 2 == y)
            )
        ):
            # table which items represents begging of all subsequences
            jump = [
                get_tile_id_from_coord(x_curr, y_curr),
                ((-1) * get_tile_id_from_coord(x_curr + 1, y_curr + 1)),
                get_tile_id_from_coord(x_curr + 2, y_curr + 2),
            ]

            tmp_prev_seq = (
                prev_seq + jump[1:]
            )  # represents prev_seq to propagate to recursive call of method
            sub_seq = CheckersGame._get_man_poss_jumps(
                tile_id, game_state, tmp_prev_seq
            )  # returns all poss sequences from next tile as table of tables

            if len(sub_seq) == 0:
                poss_jumps.append(jump)
            else:
                for i in sub_seq:
                    full_sub_seq = jump + i[1:]
                    poss_jumps.append(full_sub_seq)

        # Looking for jumps on diagonal - decreasing x and increasing y
        if (
            x_curr - 2 >= 0  # we need to move two tiles for jump
            and y_curr + 2 < 8  # we need to move two tiles for jump
            and ((-1) * get_tile_id_from_coord(x_curr - 1, y_curr + 1))
            not in prev_seq  # we cannot jump two times over same opponent piece
            and game_state[x][y] * game_state[x_curr - 1][y_curr + 1]
            < 0  # so that we have opposing side pieces
            and (  # we have empty tile after opponent (or the tile was initial jumping piece tile)
                game_state[x_curr - 2][y_curr + 2] == 0
                or (x_curr - 2 == x and y_curr + 2 == y)
            )
        ):
            jump = [  # table which items represents begging of all subsequences
                get_tile_id_from_coord(x_curr, y_curr),
                ((-1) * get_tile_id_from_coord(x_curr - 1, y_curr + 1)),
                get_tile_id_from_coord(x_curr - 2, y_curr + 2),
            ]

            tmp_prev_seq = (
                prev_seq + jump[1:]
            )  # represents prev_seq to propagate to recursive call of method
            sub_seq = CheckersGame._get_man_poss_jumps(
                tile_id, game_state, tmp_prev_seq
            )  # returns all poss sequences from next tile as table of tables

            if len(sub_seq) == 0:
                poss_jumps.append(jump)
            else:
                for i in sub_seq:
                    full_sub_seq = jump + i[1:]
                    poss_jumps.append(full_sub_seq)

        # Looking for jumps on diagonal - decreasing x and y
        if (
            x_curr - 2 >= 0  # we need to move two tiles for jump
            and y_curr - 2 >= 0  # we need to move two tiles for jump
            and ((-1) * get_tile_id_from_coord(x_curr - 1, y_curr - 1))
            not in prev_seq  # we cannot jump two times over same opponent piece
            and game_state[x][y] * game_state[x_curr - 1][y_curr - 1]
            < 0  # so that we have opposing side pieces
            and (  # we have empty tile after opponent (or the tile was initial jumping piece tile)
                game_state[x_curr - 2][y_curr - 2] == 0
                or (x_curr - 2 == x and y_curr - 2 == y)
            )
        ):
            jump = [  # table which items represents begging of all subsequences
                get_tile_id_from_coord(x_curr, y_curr),
                ((-1) * get_tile_id_from_coord(x_curr - 1, y_curr - 1)),
                get_tile_id_from_coord(x_curr - 2, y_curr - 2),
            ]

            tmp_prev_seq = (
                prev_seq + jump[1:]
            )  # represents prev_seq to propagate to recursive call of method
            sub_seq = CheckersGame._get_man_poss_jumps(
                tile_id, game_state, tmp_prev_seq
            )  # returns all poss sequences from next tile as table of tables

            if len(sub_seq) == 0:
                poss_jumps.append(jump)
            else:
                for i in sub_seq:
                    full_sub_seq = jump + i[1:]
                    poss_jumps.append(full_sub_seq)

        # Looking for jumps on diagonal - increasing x and decreasing y
        if (
            x_curr + 2 < 8  # we need to move two tiles for jump
            and y_curr - 2 >= 0  # we need to move two tiles for jump
            and ((-1) * get_tile_id_from_coord(x_curr + 1, y_curr - 1))
            not in prev_seq  # we cannot jump two times over same opponent piece
            and game_state[x][y] * game_state[x_curr + 1][y_curr - 1]
            < 0  # so that we have opposing side pieces
            and (  # we have empty tile after opponent (or the tile was initial jumping piece tile)
                game_state[x_curr + 2][y_curr - 2] == 0
                or (x_curr + 2 == x and y_curr - 2 == y)
            )
        ):
            jump = [  # table which items represents begging of all subsequences
                get_tile_id_from_coord(x_curr, y_curr),
                (-get_tile_id_from_coord(x_curr + 1, y_curr - 1)),
                get_tile_id_from_coord(x_curr + 2, y_curr - 2),
            ]

            tmp_prev_seq = (
                prev_seq + jump[1:]
            )  # represents prev_seq to propagate to recursive call of method
            sub_seq = CheckersGame._get_man_poss_jumps(
                tile_id, game_state, tmp_prev_seq
            )  # returns all poss sequences from next tile as table of tables

            if len(sub_seq) == 0:
                poss_jumps.append(jump)
            else:
                for i in sub_seq:
                    full_sub_seq = jump + i[1:]
                    poss_jumps.append(full_sub_seq)

        # filter longest sequence(s) only
        longest_num = 0
        for s in poss_jumps:
            if len(s) > longest_num:
                longest_num = len(s)
        poss_jumps[:] = [s for s in poss_jumps if len(s) == longest_num]

        return poss_jumps

    @classmethod
    def _get_king_poss_jumps(
        cls, tile_id: int, game_state: np.ndarray, prev_seq: List = None
    ):
        if prev_seq is None:
            prev_seq = []
        poss_jumps = []
        val_of_id = CheckersGame._get_value_of_tile(tile_id, game_state)

        if val_of_id not in (-2, 2):
            return None  # this tile doesn't contain a man piece of either player

        # indicate the beginning of jumping sequence
        x, y = get_coord_from_tile_id(tile_id)

        if len(prev_seq) == 0:
            x_curr = x
            y_curr = y
        else:
            x_curr, y_curr = get_coord_from_tile_id(prev_seq[len(prev_seq) - 1])

        # Looking for jumps on diagonal - increasing x and y
        x_tmp = x_curr
        y_tmp = y_curr
        while (  # this loop is meant to look if we have any poss jumps on that diagonal
            x_tmp < 8
            and y_tmp < 8
            and (game_state[x_tmp][y_tmp] == 0 or (x_tmp == x and y_tmp == y))
        ):
            if (  # true if we are ready to jump over an opponent piece
                x_tmp + 2 < 8  # we need to move two tiles for jump
                and y_tmp + 2 < 8  # we need to move two tiles for jump
                and ((-1) * get_tile_id_from_coord(x_tmp + 1, y_tmp + 1))
                not in prev_seq  # we cannot jump two times over same opponent piece
                and game_state[x][y] * game_state[x_tmp + 1][y_tmp + 1]
                < 0  # so that we have opposing side pieces
                and (  # we have empty tile after opponent (or the tile was initial jumping piece tile)
                    game_state[x_tmp + 2][y_tmp + 2] == 0
                    or (x_tmp + 2 == x and y_tmp + 2 == y)
                )
            ):
                x_after_jump = x_tmp + 2
                y_after_jump = y_tmp + 2

                # this loop is meant to go through all after jump landing possible positions
                while (
                    x_after_jump < 8
                    and y_after_jump < 8
                    and (
                        game_state[x_after_jump][y_after_jump] == 0
                        or (x_after_jump == x and y_after_jump == y)
                    )
                ):
                    # table which items represents begging of all subsequences
                    jump = [
                        get_tile_id_from_coord(x_curr, y_curr),
                        ((-1) * get_tile_id_from_coord(x_tmp + 1, y_tmp + 1)),
                        get_tile_id_from_coord(x_after_jump, y_after_jump),
                    ]
                    # represents prev_seq to propagate to recursive call of method
                    tmp_prev_seq = prev_seq + jump[1:]

                    # returns all poss sequences from next tile as table of tables
                    sub_seq = CheckersGame._get_king_poss_jumps(
                        tile_id, game_state, prev_seq=tmp_prev_seq
                    )

                    if len(sub_seq) == 0:
                        poss_jumps.append(jump)
                    else:
                        for i in sub_seq:
                            # Filtering out same seq (different mid landing for jumps over same opponent pieces)
                            # If we want to remain jumping same dir -> the convention is that we land just before next piece
                            x_next_jumped, y_next_jumped = get_coord_from_tile_id(-i[1])
                            if (
                                x_next_jumped - x_after_jump > 0
                                and y_next_jumped - y_after_jump > 0
                            ):
                                if (
                                    x_next_jumped - x_after_jump == 1
                                    and y_next_jumped - y_after_jump == 1
                                ):
                                    full_sub_seq = jump + i[1:]
                                    poss_jumps.append(full_sub_seq)
                            else:
                                full_sub_seq = jump + i[1:]
                                poss_jumps.append(full_sub_seq)

                    x_after_jump += 1
                    y_after_jump += 1

            x_tmp += 1
            y_tmp += 1

        # Looking for jumps on diagonal - decreasing x and increasing y
        x_tmp = x_curr
        y_tmp = y_curr
        while (  # this loop is meant to look if we have any poss jumps on that diagonal
            x_tmp >= 0
            and y_tmp < 8
            and (game_state[x_tmp][y_tmp] == 0 or (x_tmp == x and y_tmp == y))
        ):
            # true if we are ready to jump over an opponent piece
            if (
                # we need to move two tiles for jump
                x_tmp - 2 >= 0
                # we need to move two tiles for jump
                and y_tmp + 2 < 8
                # we cannot jump two times over same opponent piece
                and ((-1) * get_tile_id_from_coord(x_tmp - 1, y_tmp + 1))
                not in prev_seq
                # so that we have opposing side pieces
                and game_state[x][y] * game_state[x_tmp - 1][y_tmp + 1] < 0
                # we have empty tile after opponent (or the tile was initial jumping piece tile)
                and (
                    game_state[x_tmp - 2][y_tmp + 2] == 0
                    or (x_tmp - 2 == x and y_tmp + 2 == y)
                )
            ):
                x_after_jump = x_tmp - 2
                y_after_jump = y_tmp + 2
                while (  # this loop is meant to go through all after jump landing possible positions
                    x_after_jump >= 0
                    and y_after_jump < 8
                    and (
                        game_state[x_after_jump][y_after_jump] == 0
                        or (x_after_jump == x and y_after_jump == y)
                    )
                ):
                    jump = [  # table which items represents begging of all subsequences
                        get_tile_id_from_coord(x_curr, y_curr),
                        ((-1) * get_tile_id_from_coord(x_tmp - 1, y_tmp + 1)),
                        get_tile_id_from_coord(x_after_jump, y_after_jump),
                    ]
                    tmp_prev_seq = (
                        prev_seq + jump[1:]
                    )  # represents prev_seq to propagate to recursive call of method
                    sub_seq = CheckersGame._get_king_poss_jumps(
                        tile_id, game_state, prev_seq=tmp_prev_seq
                    )  # returns all poss sequences from next tile as table of tables

                    if len(sub_seq) == 0:
                        poss_jumps.append(jump)
                    else:
                        for i in sub_seq:
                            # Filtering out same seq (different mid landing for jumps over same opponent pieces)
                            # If we want to remain jumping same dir -> the convention is that we land just before next piece
                            x_next_jumped, y_next_jumped = get_coord_from_tile_id(-i[1])
                            if (
                                x_next_jumped - x_after_jump < 0
                                and y_next_jumped - y_after_jump > 0
                            ):
                                if (
                                    x_next_jumped - x_after_jump == -1
                                    and y_next_jumped - y_after_jump == 1
                                ):
                                    full_sub_seq = jump + i[1:]
                                    poss_jumps.append(full_sub_seq)
                            else:
                                full_sub_seq = jump + i[1:]
                                poss_jumps.append(full_sub_seq)

                    x_after_jump -= 1
                    y_after_jump += 1

            x_tmp -= 1
            y_tmp += 1

        # Looking for jumps on diagonal - decreasing x and y
        x_tmp = x_curr
        y_tmp = y_curr
        while (  # this loop is meant to look if we have any poss jumps on that diagonal
            x_tmp >= 0
            and y_tmp >= 0
            and (game_state[x_tmp][y_tmp] == 0 or (x_tmp == x and y_tmp == y))
        ):
            if (  # true if we are ready to jump over an opponent piece
                x_tmp - 2 >= 0  # we need to move two tiles for jump
                and y_tmp - 2 >= 0  # we need to move two tiles for jump
                and ((-1) * get_tile_id_from_coord(x_tmp - 1, y_tmp - 1))
                not in prev_seq  # we cannot jump two times over same opponent piece
                and game_state[x][y] * game_state[x_tmp - 1][y_tmp - 1]
                < 0  # so that we have opposing side pieces
                and (  # we have empty tile after opponent (or the tile was initial jumping piece tile)
                    game_state[x_tmp - 2][y_tmp - 2] == 0
                    or (x_tmp - 2 == x and y_tmp - 2 == y)
                )
            ):
                x_after_jump = x_tmp - 2
                y_after_jump = y_tmp - 2
                while (  # this loop is meant to go through all after jump landing possible positions
                    x_after_jump >= 0
                    and y_after_jump >= 0
                    and (
                        game_state[x_after_jump][y_after_jump] == 0
                        or (x_after_jump == x and y_after_jump == y)
                    )
                ):
                    jump = [  # table which items represents begging of all subsequences
                        get_tile_id_from_coord(x_curr, y_curr),
                        ((-1) * get_tile_id_from_coord(x_tmp - 1, y_tmp - 1)),
                        get_tile_id_from_coord(x_after_jump, y_after_jump),
                    ]
                    tmp_prev_seq = (
                        prev_seq + jump[1:]
                    )  # represents prev_seq to propagate to recursive call of method
                    sub_seq = CheckersGame._get_king_poss_jumps(
                        tile_id, game_state, prev_seq=tmp_prev_seq
                    )  # returns all poss sequences from next tile as table of tables

                    if len(sub_seq) == 0:
                        poss_jumps.append(jump)
                    else:
                        for i in sub_seq:
                            # Filtering out same seq (different mid landing for jumps over same opponent pieces)
                            # If we want to remain jumping same dir -> the convention is that we land just before next piece
                            x_next_jumped, y_next_jumped = get_coord_from_tile_id(-i[1])
                            if (
                                x_next_jumped - x_after_jump < 0
                                and y_next_jumped - y_after_jump < 0
                            ):
                                if (
                                    x_next_jumped - x_after_jump == -1
                                    and y_next_jumped - y_after_jump == -1
                                ):
                                    full_sub_seq = jump + i[1:]
                                    poss_jumps.append(full_sub_seq)
                            else:
                                full_sub_seq = jump + i[1:]
                                poss_jumps.append(full_sub_seq)

                    x_after_jump -= 1
                    y_after_jump -= 1

            x_tmp -= 1
            y_tmp -= 1

        # Looking for jumps on diagonal - increasing x and decreasing y
        x_tmp = x_curr
        y_tmp = y_curr
        # this loop is meant to look if we have any poss jumps on that diagonal
        while (
            x_tmp < 8
            and y_tmp >= 0
            and (game_state[x_tmp][y_tmp] == 0 or (x_tmp == x and y_tmp == y))
        ):
            # true if we are ready to jump over an opponent piece
            if (
                # we need to move two tiles for jump
                x_tmp + 2 < 8
                # we need to move two tiles for jump
                and y_tmp - 2 >= 0
                # we cannot jump two times over same opponent piece
                and ((-1) * get_tile_id_from_coord(x_tmp + 1, y_tmp - 1))
                not in prev_seq
                # so that we have opposing side pieces
                and game_state[x][y] * game_state[x_tmp + 1][y_tmp - 1] < 0
                # we have empty tile after opponent (or the tile was initial jumping piece tile)
                and (
                    game_state[x_tmp + 2][y_tmp - 2] == 0
                    or (x_tmp + 2 == x and y_tmp - 2 == y)
                )
            ):
                x_after_jump = x_tmp + 2
                y_after_jump = y_tmp - 2

                # this loop is meant to go through all after jump landing possible positions
                while (
                    x_after_jump < 8
                    and y_after_jump >= 0
                    and (
                        game_state[x_after_jump][y_after_jump] == 0
                        or (x_after_jump == x and y_after_jump == y)
                    )
                ):
                    jump = [  # table which items represents begging of all subsequences
                        get_tile_id_from_coord(x_curr, y_curr),
                        ((-1) * get_tile_id_from_coord(x_tmp + 1, y_tmp - 1)),
                        get_tile_id_from_coord(x_after_jump, y_after_jump),
                    ]
                    # represents prev_seq to propagate to recursive call of method
                    tmp_prev_seq = prev_seq + jump[1:]
                    # returns all poss sequences from next tile as table of tables
                    sub_seq = CheckersGame._get_king_poss_jumps(
                        tile_id, game_state, prev_seq=tmp_prev_seq
                    )

                    if len(sub_seq) == 0:
                        poss_jumps.append(jump)
                    else:
                        for i in sub_seq:
                            # Filtering out same seq (different mid landing for jumps over same opponent pieces)
                            # If we want to remain jumping same dir -> the convention is that we land just before next piece
                            x_next_jumped, y_next_jumped = get_coord_from_tile_id(-i[1])
                            if (
                                x_next_jumped - x_after_jump > 0
                                and y_next_jumped - y_after_jump < 0
                            ):
                                if (
                                    x_next_jumped - x_after_jump == 1
                                    and y_next_jumped - y_after_jump == -1
                                ):
                                    full_sub_seq = jump + i[1:]
                                    poss_jumps.append(full_sub_seq)
                            else:
                                full_sub_seq = jump + i[1:]
                                poss_jumps.append(full_sub_seq)

                    x_after_jump += 1
                    y_after_jump -= 1

            x_tmp += 1
            y_tmp -= 1

        # filter longest sequence(s) only
        longest_num = 0
        for s in poss_jumps:
            longest_num = max(longest_num, len(s))
        poss_jumps[:] = [s for s in poss_jumps if len(s) == longest_num]

        return poss_jumps

    @classmethod
    def get_color_poss_opts(cls, color: Color, game_state: np.ndarray):
        poss_opts: list = []

        # gather all options disregarding their length or move/jump diff
        for x, _ in enumerate(game_state):  # iterate all tiles for pieces
            for y, _ in enumerate(game_state[x]):
                tile_id: int = get_tile_id_from_coord(x, y)

                # if king -> check if jump or move of king possible
                if color.value * game_state[x][y] == 2:
                    # must be either ORANGE or BLUE king, depending on color given
                    opts = CheckersGame._get_king_poss_jumps(tile_id, game_state)
                    poss_opts += opts

                    opts = CheckersGame._get_king_poss_moves(tile_id, game_state)
                    poss_opts += opts

                # if man -> check if jump or move of man possible
                if color.value * game_state[x][y] == 1:
                    # must be either ORANGE or BLUE king, depending on color given
                    opts = CheckersGame._get_man_poss_jumps(tile_id, game_state)
                    poss_opts += opts

                    opts = CheckersGame._get_man_poss_moves(tile_id, game_state)
                    poss_opts += opts

        # filter longest sequence(s) only
        longest_num = 0
        for s in poss_opts:
            longest_num = max(longest_num, len(s))
        poss_opts[:] = [s for s in poss_opts if len(s) == longest_num]

        return poss_opts

    @classmethod
    def get_outcome_of_move(cls, state: np.ndarray, move):
        x_tmp, y_tmp = get_coord_from_tile_id(move[0])
        val_of_piece = state[x_tmp][y_tmp]
        state[x_tmp][y_tmp] = 0  # Remove moving piece from start position

        # Remove all jumped over pieces
        for i in move:
            if i < 0:
                x_tmp, y_tmp = get_coord_from_tile_id(-i)
                state[x_tmp][y_tmp] = 0

        x_tmp, y_tmp = get_coord_from_tile_id(move[len(move) - 1])
        if val_of_piece == 1 and y_tmp == 7:
            # Crown if crowning needed, else just place at the end of sequence
            state[x_tmp][y_tmp] = 2
        elif val_of_piece == -1 and y_tmp == 0:
            state[x_tmp][y_tmp] = -2
        else:
            state[x_tmp][y_tmp] = val_of_piece

        return state

    def get_game_state(self):
        return deepcopy(self.game_state)

    def get_draw_criteria_log(self):
        return deepcopy(self.draw_criteria_log)

    def get_status(self):
        return self.status

    def get_winning_player(self):
        return self.winning_player

    def get_points(self):
        return {Color.ORANGE: self.orange_score, Color.BLUE: self.blue_score}

    def get_possible_opts(self):
        return deepcopy(self.turn_player_opts)

    def get_possible_outcomes(self):
        # Returns a dict of pairs move: outcome
        possible_outcomes = []

        for i in self.get_possible_opts():
            outcome = self.get_game_state()
            outcome = CheckersGame.get_outcome_of_move(outcome, i)
            possible_outcomes.append([i, outcome])

        return possible_outcomes

    def get_turn_of(self) -> Optional[Color]:
        if self.status == Status.IN_PROGRESS:
            return self.turn_of
        return None

    def perform_move(self, sequence):
        if self.status != Status.IN_PROGRESS:
            raise CheckersGameEndError("Game already ended")

        if sequence not in self.turn_player_opts:
            raise CheckersGameNotPermittedMoveError("Movement not permitted")

        x_tmp, y_tmp = get_coord_from_tile_id(sequence[0])
        val_of_piece = self.game_state[x_tmp][y_tmp]
        self.game_state[x_tmp][y_tmp] = 0  # Remove moving piece from start position

        has_jumped = False
        # Remove all jumped over pieces
        for i in sequence:
            if i < 0:
                x_tmp, y_tmp = get_coord_from_tile_id(-i)
                self.game_state[x_tmp][y_tmp] = 0
                if self.turn_of == Color.BLUE:
                    self.blue_score += 1
                else:
                    self.orange_score += 1
                has_jumped = True

        # Jumping results in draw criteria log being restarted
        if has_jumped:
            self.draw_criteria_log = []

        x_tmp, y_tmp = get_coord_from_tile_id(sequence[len(sequence) - 1])

        # Crown if crowning needed, else just place at the end of sequence
        if val_of_piece == 1 and y_tmp == 7:
            self.game_state[x_tmp][y_tmp] = 2
        elif val_of_piece == -1 and y_tmp == 0:
            self.game_state[x_tmp][y_tmp] = -2
        else:
            self.game_state[x_tmp][y_tmp] = val_of_piece

        self.log.append(sequence)  # log sequence

        opponent = Color.BLUE if self.turn_of == Color.ORANGE else Color.ORANGE

        # Check for draw criteria
        self.draw_criteria_log.append((opponent, self.get_game_state()))

        draw_criteria_count = 0
        for i in self.draw_criteria_log:
            if np.array_equal(i[0], opponent) and np.array_equal(i[1], self.game_state):
                draw_criteria_count += 1
        if draw_criteria_count >= 3:
            self.status = Status.DRAW

        # Check for winning criteria, if game still in progress
        if self.status == Status.IN_PROGRESS:
            self.turn_player_opts = CheckersGame.get_color_poss_opts(
                opponent, self.game_state
            )
            if len(self.turn_player_opts) == 0:
                self.status = Status.WON
                self.winning_player = self.turn_of

        self.turn_of = opponent

        return self.status
