from src.checkers_game_and_decissions.enum_entities import Status
from src.checkers_game_and_decissions.utilities import *


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
        #       -0 is an empty field
        #   - game state is 2d matrix:
        #       - it is to be perceived as list of columns
        #       - the orange are on the upper side
        #       - the game_state[0][0] is the upper left field
        #       - the game_state[7][7] is the bottom right field
        #       - the upper side is y = 0
        #       - the bottom side is y = 7
        self.game_state = [
            [0, 1, 0, 0, 0, -1, 0, -1],
            [1, 0, 1, 0, 0, 0, -1, 0],
            [0, 1, 0, 0, 0, -1, 0, -1],
            [1, 0, 1, 0, 0, 0, -1, 0],
            [0, 1, 0, 0, 0, -1, 0, -1],
            [1, 0, 1, 0, 0, 0, -1, 0],
            [0, 1, 0, 0, 0, -1, 0, -1],
            [1, 0, 1, 0, 0, 0, -1, 0],
        ]

        # First move always goes to BLUE (in normal gameplay - white)
        self.turn_of = Color.BLUE

        self.turn_player_opts = CheckersGame.get_color_poss_opts(
            self.turn_of, self.game_state
        )

        # log of gameplay is saved as list of lists (each 'smaller' list is of integers - each represents id of field - see rules_desc)
        # each one round movement is a list of integers:
        #   -> first item is starting id of a moved piece
        #   -> each positive integer then is id of next field the piece landed on
        #   -> each negative integer indicates id of field that the opponent piece was jumped over
        #   -> for single move - the list has two items (both positive)
        #   -> for jumping sequence -> the list has odd number of items and goes [+, -, ... , +]
        self.log = []

        # will be a list of tuples, where tuple[0] is player having turn, and tuple [1] is game_state
        self.draw_criteria_log = [(self.turn_of, self.get_game_state())]

        self.ORANGE_points = 0
        self.BLUE_points = 0

        self.status = Status.IN_PROGRESS
        self.winning_player = None  # will be filled with Color.ORANGE/Color.BLUE if state becomes Status.WON

    @classmethod
    def get_value_of_field(cls, id, game_state):
        x, y = get_coord_from_field_id(id)

        return game_state[x][y]

    @classmethod
    def get_man_poss_moves(cls, id, game_state):
        poss_moves = []
        val_of_id = CheckersGame.get_value_of_field(id, game_state)

        if val_of_id != 1 and val_of_id != -1:
            return None  # this field doesn't contain a man piece of either player

        if val_of_id == 1:  # ORANGE -> moves 'down' towards bigger ids
            x, y = get_coord_from_field_id(id)  # poss moves to x-1,y+1 or x+1, y+!
            if y + 1 == 8:
                return None  # piece should have been crowned and was mistakenly treated as man
            else:
                if x - 1 >= 0 and game_state[x - 1][y + 1] == 0:
                    poss_moves.append([id, get_field_id_from_coord(x - 1, y + 1)])
                if x + 1 < 8 and game_state[x + 1][y + 1] == 0:
                    poss_moves.append([id, get_field_id_from_coord(x + 1, y + 1)])

        else:  # BLUE -> moves 'up' towards lower ids
            x, y = get_coord_from_field_id(id)
            if y == 0:
                return None  # piece should have been crowned and was mistakenly treated as man
            else:
                if x - 1 >= 0 and game_state[x - 1][y - 1] == 0:
                    poss_moves.append([id, get_field_id_from_coord(x - 1, y - 1)])
                if x + 1 < 8 and game_state[x + 1][y - 1] == 0:
                    poss_moves.append([id, get_field_id_from_coord(x + 1, y - 1)])

        return poss_moves

    @classmethod
    def get_king_poss_moves(cls, id, game_state):
        poss_moves = []
        val_of_id = CheckersGame.get_value_of_field(id, game_state)

        if val_of_id != 2 and val_of_id != -2:
            return None  # this field doesn't contain a king piece of either player

        x, y = get_coord_from_field_id(id)

        # Diagonal of increasing x and y
        x_tmp = x + 1
        y_tmp = y + 1
        while x_tmp < 8 and y_tmp < 8 and game_state[x_tmp][y_tmp] == 0:
            poss_moves.append([id, get_field_id_from_coord(x_tmp, y_tmp)])
            x_tmp += 1
            y_tmp += 1

        # Diagonal of decreasing x and increasing y
        x_tmp = x - 1
        y_tmp = y + 1
        while x_tmp >= 0 and y_tmp < 8 and game_state[x_tmp][y_tmp] == 0:
            poss_moves.append([id, get_field_id_from_coord(x_tmp, y_tmp)])
            x_tmp -= 1
            y_tmp += 1

        # Diagonal of decreasing x and y
        x_tmp = x - 1
        y_tmp = y - 1
        while x_tmp >= 0 and y_tmp >= 0 and game_state[x_tmp][y_tmp] == 0:
            poss_moves.append([id, get_field_id_from_coord(x_tmp, y_tmp)])
            x_tmp -= 1
            y_tmp -= 1

        # Diagonal of increasing x and decreasing y
        x_tmp = x + 1
        y_tmp = y - 1
        while x_tmp < 8 and y_tmp >= 0 and game_state[x_tmp][y_tmp] == 0:
            poss_moves.append([id, get_field_id_from_coord(x_tmp, y_tmp)])
            x_tmp += 1
            y_tmp -= 1

        return poss_moves

    @classmethod
    def get_man_poss_jumps(cls, id, game_state, prev_seq=None):
        if prev_seq is None:
            prev_seq = []
        poss_jumps = []
        val_of_id = CheckersGame.get_value_of_field(id, game_state)

        if val_of_id != 1 and val_of_id != -1:
            return None  # this field doesn't contain a man piece of either player

        x, y = get_coord_from_field_id(id)

        if len(prev_seq) == 0:
            x_curr = x
            y_curr = y
        else:
            x_curr, y_curr = get_coord_from_field_id(prev_seq[len(prev_seq) - 1])

        # Looking for jumps on diagonal - increasing x and y
        if (
                x_curr + 2 < 8  # we need to move two fields for jump
                and y_curr + 2 < 8  # we need to move two fields for jump
                and ((-1) * get_field_id_from_coord(x_curr + 1, y_curr + 1))
                not in prev_seq  # we cannot jump two times over same opponent piece
                and game_state[x][y] * game_state[x_curr + 1][y_curr + 1]
                < 0  # so that we have opposing side pieces
                and (  # we have empty field after opponent (or the field was initial jumping piece field)
                game_state[x_curr + 2][y_curr + 2] == 0
                or (x_curr + 2 == x and y_curr + 2 == y)
        )
        ):
            jump = [  # table which items represents begging of all subsequences
                get_field_id_from_coord(x_curr, y_curr),
                ((-1) * get_field_id_from_coord(x_curr + 1, y_curr + 1)),
                get_field_id_from_coord(x_curr + 2, y_curr + 2),
            ]

            tmp_prev_seq = (
                    prev_seq + jump[1:]
            )  # represents prev_seq to propagate to recursive call of method
            sub_seq = CheckersGame.get_man_poss_jumps(
                id, game_state, tmp_prev_seq
            )  # returns all poss sequences from next field as table of tables

            if len(sub_seq) == 0:
                poss_jumps.append(jump)
            else:
                for i in sub_seq:
                    full_sub_seq = jump + i[1:]
                    poss_jumps.append(full_sub_seq)

        # Looking for jumps on diagonal - decreasing x and increasing y
        if (
                x_curr - 2 >= 0  # we need to move two fields for jump
                and y_curr + 2 < 8  # we need to move two fields for jump
                and ((-1) * get_field_id_from_coord(x_curr - 1, y_curr + 1))
                not in prev_seq  # we cannot jump two times over same opponent piece
                and game_state[x][y] * game_state[x_curr - 1][y_curr + 1]
                < 0  # so that we have opposing side pieces
                and (  # we have empty field after opponent (or the field was initial jumping piece field)
                game_state[x_curr - 2][y_curr + 2] == 0
                or (x_curr - 2 == x and y_curr + 2 == y)
        )
        ):
            jump = [  # table which items represents begging of all subsequences
                get_field_id_from_coord(x_curr, y_curr),
                ((-1) * get_field_id_from_coord(x_curr - 1, y_curr + 1)),
                get_field_id_from_coord(x_curr - 2, y_curr + 2),
            ]

            tmp_prev_seq = (
                    prev_seq + jump[1:]
            )  # represents prev_seq to propagate to recursive call of method
            sub_seq = CheckersGame.get_man_poss_jumps(
                id, game_state, tmp_prev_seq
            )  # returns all poss sequences from next field as table of tables

            if len(sub_seq) == 0:
                poss_jumps.append(jump)
            else:
                for i in sub_seq:
                    full_sub_seq = jump + i[1:]
                    poss_jumps.append(full_sub_seq)

        # Looking for jumps on diagonal - decreasing x and y
        if (
                x_curr - 2 >= 0  # we need to move two fields for jump
                and y_curr - 2 >= 0  # we need to move two fields for jump
                and ((-1) * get_field_id_from_coord(x_curr - 1, y_curr - 1))
                not in prev_seq  # we cannot jump two times over same opponent piece
                and game_state[x][y] * game_state[x_curr - 1][y_curr - 1]
                < 0  # so that we have opposing side pieces
                and (  # we have empty field after opponent (or the field was initial jumping piece field)
                game_state[x_curr - 2][y_curr - 2] == 0
                or (x_curr - 2 == x and y_curr - 2 == y)
        )
        ):
            jump = [  # table which items represents begging of all subsequences
                get_field_id_from_coord(x_curr, y_curr),
                ((-1) * get_field_id_from_coord(x_curr - 1, y_curr - 1)),
                get_field_id_from_coord(x_curr - 2, y_curr - 2),
            ]

            tmp_prev_seq = (
                    prev_seq + jump[1:]
            )  # represents prev_seq to propagate to recursive call of method
            sub_seq = CheckersGame.get_man_poss_jumps(
                id, game_state, tmp_prev_seq
            )  # returns all poss sequences from next field as table of tables

            if len(sub_seq) == 0:
                poss_jumps.append(jump)
            else:
                for i in sub_seq:
                    full_sub_seq = jump + i[1:]
                    poss_jumps.append(full_sub_seq)

        # Looking for jumps on diagonal - increasing x and decreasing y
        if (
                x_curr + 2 < 8  # we need to move two fields for jump
                and y_curr - 2 >= 0  # we need to move two fields for jump
                and ((-1) * get_field_id_from_coord(x_curr + 1, y_curr - 1))
                not in prev_seq  # we cannot jump two times over same opponent piece
                and game_state[x][y] * game_state[x_curr + 1][y_curr - 1]
                < 0  # so that we have opposing side pieces
                and (  # we have empty field after opponent (or the field was initial jumping piece field)
                game_state[x_curr + 2][y_curr - 2] == 0
                or (x_curr + 2 == x and y_curr - 2 == y)
        )
        ):
            jump = [  # table which items represents begging of all subsequences
                get_field_id_from_coord(x_curr, y_curr),
                ((-1) * get_field_id_from_coord(x_curr + 1, y_curr - 1)),
                get_field_id_from_coord(x_curr + 2, y_curr - 2),
            ]

            tmp_prev_seq = (
                    prev_seq + jump[1:]
            )  # represents prev_seq to propagate to recursive call of method
            sub_seq = CheckersGame.get_man_poss_jumps(
                id, game_state, tmp_prev_seq
            )  # returns all poss sequences from next field as table of tables

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
    def get_king_poss_jumps(cls, id, game_state, prev_seq=None):
        if prev_seq is None:
            prev_seq = []
        poss_jumps = []
        val_of_id = CheckersGame.get_value_of_field(id, game_state)

        if val_of_id != 2 and val_of_id != -2:
            return None  # this field doesn't contain a man piece of either player

        x, y = get_coord_from_field_id(id)  # indicate the beginning of jumping sequence

        if len(prev_seq) == 0:
            x_curr = x
            y_curr = y
        else:
            x_curr, y_curr = get_coord_from_field_id(prev_seq[len(prev_seq) - 1])

        # Looking for jumps on diagonal - increasing x and y
        x_tmp = x_curr
        y_tmp = y_curr
        while (  # this loop is meant to look if we have any poss jumps on that diagonal
                x_tmp < 8
                and y_tmp < 8
                and (game_state[x_tmp][y_tmp] == 0 or (x_tmp == x and y_tmp == y))
        ):
            if (  # true if we are ready to jump over an opponent piece
                    x_tmp + 2 < 8  # we need to move two fields for jump
                    and y_tmp + 2 < 8  # we need to move two fields for jump
                    and ((-1) * get_field_id_from_coord(x_tmp + 1, y_tmp + 1))
                    not in prev_seq  # we cannot jump two times over same opponent piece
                    and game_state[x][y] * game_state[x_tmp + 1][y_tmp + 1]
                    < 0  # so that we have opposing side pieces
                    and (  # we have empty field after opponent (or the field was initial jumping piece field)
                    game_state[x_tmp + 2][y_tmp + 2] == 0
                    or (x_tmp + 2 == x and y_tmp + 2 == y)
            )
            ):
                x_after_jump = x_tmp + 2
                y_after_jump = y_tmp + 2
                while (  # this loop is meant to go through all after jump landing possible positions
                        x_after_jump < 8
                        and y_after_jump < 8
                        and (
                                game_state[x_after_jump][y_after_jump] == 0
                                or (x_after_jump == x and y_after_jump == y)
                        )
                ):
                    jump = (
                        [  # table which items represents begging of all subsequences
                            get_field_id_from_coord(x_curr, y_curr),
                            ((-1) * get_field_id_from_coord(x_tmp + 1, y_tmp + 1)),
                            get_field_id_from_coord(x_after_jump, y_after_jump),
                        ]
                    )
                    tmp_prev_seq = (
                            prev_seq + jump[1:]
                    )  # represents prev_seq to propagate to recursive call of method
                    sub_seq = CheckersGame.get_king_poss_jumps(
                        id, game_state, prev_seq=tmp_prev_seq
                    )  # returns all poss sequences from next field as table of tables

                    if len(sub_seq) == 0:
                        poss_jumps.append(jump)
                    else:
                        for i in sub_seq:
                            # Filtering out same seq (different mid landing for jumps over same opponent pieces)
                            # If we want to remain jumping same dir -> the convention is that we land just before next piece
                            x_next_jumped, y_next_jumped = get_coord_from_field_id(
                                -i[1]
                            )
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
            if (  # true if we are ready to jump over an opponent piece
                    x_tmp - 2 >= 0  # we need to move two fields for jump
                    and y_tmp + 2 < 8  # we need to move two fields for jump
                    and ((-1) * get_field_id_from_coord(x_tmp - 1, y_tmp + 1))
                    not in prev_seq  # we cannot jump two times over same opponent piece
                    and game_state[x][y] * game_state[x_tmp - 1][y_tmp + 1]
                    < 0  # so that we have opposing side pieces
                    and (  # we have empty field after opponent (or the field was initial jumping piece field)
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
                    jump = (
                        [  # table which items represents begging of all subsequences
                            get_field_id_from_coord(x_curr, y_curr),
                            ((-1) * get_field_id_from_coord(x_tmp - 1, y_tmp + 1)),
                            get_field_id_from_coord(x_after_jump, y_after_jump),
                        ]
                    )
                    tmp_prev_seq = (
                            prev_seq + jump[1:]
                    )  # represents prev_seq to propagate to recursive call of method
                    sub_seq = CheckersGame.get_king_poss_jumps(
                        id, game_state, prev_seq=tmp_prev_seq
                    )  # returns all poss sequences from next field as table of tables

                    if len(sub_seq) == 0:
                        poss_jumps.append(jump)
                    else:
                        for i in sub_seq:
                            # Filtering out same seq (different mid landing for jumps over same opponent pieces)
                            # If we want to remain jumping same dir -> the convention is that we land just before next piece
                            x_next_jumped, y_next_jumped = get_coord_from_field_id(
                                -i[1]
                            )
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
                    x_tmp - 2 >= 0  # we need to move two fields for jump
                    and y_tmp - 2 >= 0  # we need to move two fields for jump
                    and ((-1) * get_field_id_from_coord(x_tmp - 1, y_tmp - 1))
                    not in prev_seq  # we cannot jump two times over same opponent piece
                    and game_state[x][y] * game_state[x_tmp - 1][y_tmp - 1]
                    < 0  # so that we have opposing side pieces
                    and (  # we have empty field after opponent (or the field was initial jumping piece field)
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
                    jump = (
                        [  # table which items represents begging of all subsequences
                            get_field_id_from_coord(x_curr, y_curr),
                            ((-1) * get_field_id_from_coord(x_tmp - 1, y_tmp - 1)),
                            get_field_id_from_coord(x_after_jump, y_after_jump),
                        ]
                    )
                    tmp_prev_seq = (
                            prev_seq + jump[1:]
                    )  # represents prev_seq to propagate to recursive call of method
                    sub_seq = CheckersGame.get_king_poss_jumps(
                        id, game_state, prev_seq=tmp_prev_seq
                    )  # returns all poss sequences from next field as table of tables

                    if len(sub_seq) == 0:
                        poss_jumps.append(jump)
                    else:
                        for i in sub_seq:
                            # Filtering out same seq (different mid landing for jumps over same opponent pieces)
                            # If we want to remain jumping same dir -> the convention is that we land just before next piece
                            x_next_jumped, y_next_jumped = get_coord_from_field_id(
                                -i[1]
                            )
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
        while (  # this loop is meant to look if we have any poss jumps on that diagonal
                x_tmp < 8
                and y_tmp >= 0
                and (game_state[x_tmp][y_tmp] == 0 or (x_tmp == x and y_tmp == y))
        ):
            if (  # true if we are ready to jump over an opponent piece
                    x_tmp + 2 < 8  # we need to move two fields for jump
                    and y_tmp - 2 >= 0  # we need to move two fields for jump
                    and ((-1) * get_field_id_from_coord(x_tmp + 1, y_tmp - 1))
                    not in prev_seq  # we cannot jump two times over same opponent piece
                    and game_state[x][y] * game_state[x_tmp + 1][y_tmp - 1]
                    < 0  # so that we have opposing side pieces
                    and (  # we have empty field after opponent (or the field was initial jumping piece field)
                    game_state[x_tmp + 2][y_tmp - 2] == 0
                    or (x_tmp + 2 == x and y_tmp - 2 == y)
            )
            ):
                x_after_jump = x_tmp + 2
                y_after_jump = y_tmp - 2
                while (  # this loop is meant to go through all after jump landing possible positions
                        x_after_jump < 8
                        and y_after_jump >= 0
                        and (
                                game_state[x_after_jump][y_after_jump] == 0
                                or (x_after_jump == x and y_after_jump == y)
                        )
                ):
                    jump = (
                        [  # table which items represents begging of all subsequences
                            get_field_id_from_coord(x_curr, y_curr),
                            ((-1) * get_field_id_from_coord(x_tmp + 1, y_tmp - 1)),
                            get_field_id_from_coord(x_after_jump, y_after_jump),
                        ]
                    )
                    tmp_prev_seq = (
                            prev_seq + jump[1:]
                    )  # represents prev_seq to propagate to recursive call of method
                    sub_seq = CheckersGame.get_king_poss_jumps(
                        id, game_state, prev_seq=tmp_prev_seq
                    )  # returns all poss sequences from next field as table of tables

                    if len(sub_seq) == 0:
                        poss_jumps.append(jump)
                    else:
                        for i in sub_seq:
                            # Filtering out same seq (different mid landing for jumps over same opponent pieces)
                            # If we want to remain jumping same dir -> the convention is that we land just before next piece
                            x_next_jumped, y_next_jumped = get_coord_from_field_id(
                                -i[1]
                            )
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
            if len(s) > longest_num:
                longest_num = len(s)
        poss_jumps[:] = [s for s in poss_jumps if len(s) == longest_num]

        return poss_jumps

    @classmethod
    def get_color_poss_opts(cls, color, game_state):
        poss_opts = []

        # gather all options disregarding their length or move/jump diff
        for x, _ in enumerate(game_state):  # iterate all fields for pieces
            for y, _ in enumerate(game_state[x]):
                id = get_field_id_from_coord(x, y)

                # if king -> check if jump or move of king possible
                if (
                        color.value * game_state[x][y] == 2
                ):  # must be either ORANGE or BLUE king, depending on color given
                    opts = CheckersGame.get_king_poss_jumps(id, game_state)
                    poss_opts += opts

                    opts = CheckersGame.get_king_poss_moves(id, game_state)
                    poss_opts += opts

                # if man -> check if jump or move of man possible
                if (
                        color.value * game_state[x][y] == 1
                ):  # must be either ORANGE or BLUE king, depending on color given
                    opts = CheckersGame.get_man_poss_jumps(id, game_state)
                    poss_opts += opts

                    opts = CheckersGame.get_man_poss_moves(id, game_state)
                    poss_opts += opts

        # filter longest sequence(s) only
        longest_num = 0
        for s in poss_opts:
            if len(s) > longest_num:
                longest_num = len(s)
        poss_opts[:] = [s for s in poss_opts if len(s) == longest_num]

        return poss_opts

    @classmethod
    def check_if_won(cls, color_opponent_turn, game_state):

        if len(CheckersGame.get_color_poss_opts(color_opponent_turn, game_state)) == 0:
            return True

        return False

    @classmethod
    def get_outcome_of_move(cls, state, move):
        x_tmp, y_tmp = get_coord_from_field_id(move[0])
        val_of_piece = state[x_tmp][y_tmp]
        state[x_tmp][y_tmp] = 0  # Remove moving piece from start position

        for i in move:  # Remove all jumped over pieces
            if i < 0:
                x_tmp, y_tmp = get_coord_from_field_id(-i)
                state[x_tmp][y_tmp] = 0

        x_tmp, y_tmp = get_coord_from_field_id(move[len(move) - 1])
        if (
                val_of_piece == 1 and y_tmp == 7
        ):  # Crown if crowning needed, else just place at the end of sequence
            state[x_tmp][y_tmp] = 2
        elif val_of_piece == -1 and y_tmp == 0:
            state[x_tmp][y_tmp] = -2
        else:
            state[x_tmp][y_tmp] = val_of_piece

        return state

    def get_game_state(self):
        return [
            i.copy() for i in self.game_state
        ]  # to make a true copy, i need to copy each internal list

    def get_log(self):
        return [
            i.copy() for i in self.log
        ]  # to make a true copy, i need to copy each internal list

    def get_draw_criteria_log(self):
        draw_crit_log = []
        for i in self.draw_criteria_log:
            draw_crit_log.append((i[0], [j.copy() for j in i[1]]))
        return draw_crit_log  # to make a true copy, i need to copy each internal list

    def get_status(self):
        return self.status

    def get_winning_player(self):
        return self.winning_player

    def get_points(self):
        return {Color.ORANGE: self.ORANGE_points, Color.BLUE: self.BLUE_points}

    def get_possible_opts(self):
        return [
            i.copy() for i in self.turn_player_opts
        ]  # to make a true copy, i need to copy each internal list

    def get_possible_outcomes(self):  # Returns a dict of pairs move: outcome
        possible_outcomes = []

        for i in self.get_possible_opts():
            outcome = self.get_game_state()
            outcome = CheckersGame.get_outcome_of_move(outcome, i)
            possible_outcomes.append([i, outcome])

        return possible_outcomes

    def get_turn_of(self):
        if self.status == Status.IN_PROGRESS:
            return self.turn_of
        else:
            return None

    def perform_move(self, sequence):

        if self.status != Status.IN_PROGRESS:
            raise Exception("Game already ended")

        if not (sequence in self.turn_player_opts):
            raise Exception("Movement not permitted")

        x_tmp, y_tmp = get_coord_from_field_id(sequence[0])
        val_of_piece = self.game_state[x_tmp][y_tmp]
        self.game_state[x_tmp][y_tmp] = 0  # Remove moving piece from start position

        has_jumped = False
        for i in sequence:  # Remove all jumped over pieces
            if i < 0:
                x_tmp, y_tmp = get_coord_from_field_id(-i)
                self.game_state[x_tmp][y_tmp] = 0
                if self.turn_of == Color.BLUE:
                    self.BLUE_points += 1
                else:
                    self.ORANGE_points += 1
                has_jumped = True

        if has_jumped:
            self.draw_criteria_log = (
                []
            )  # Jumping results in draw criteria log being restarted

        x_tmp, y_tmp = get_coord_from_field_id(sequence[len(sequence) - 1])
        if (
                val_of_piece == 1 and y_tmp == 7
        ):  # Crown if crowning needed, else just place at the end of sequence
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
            if i[0] == opponent and i[1] == self.game_state:
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


def test():
    game = CheckersGame()

    game.game_state = [
        [0, 1, 0, 0, 0, -1, 0, -1],
        [1, 0, 1, 0, 0, 0, -1, 0],
        [0, 1, 0, 0, 0, -1, 0, -1],
        [1, 0, 1, 0, 0, 0, -1, 0],
        [0, 1, 0, 0, 0, -1, 0, -1],
        [1, 0, 0, 0, 1, 0, -1, 0],
        [0, 1, 0, 0, 0, -2, 0, -1],
        [1, 0, 1, 0, 0, 0, -1, 0],
    ]

    print(CheckersGame.get_color_poss_opts(Color.BLUE, game.get_game_state()))


if __name__ == "__main__":
    test()
