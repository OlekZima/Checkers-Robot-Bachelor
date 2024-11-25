from src.checkers_game_and_decisions.checkers_game import CheckersGame
from src.checkers_game_and_decisions.enum_entities import Color

import numpy as np

import time


class NegamaxDecisionEngine:

    ASSESSMENT_VALUE_MAX_AMPLITUDE = 24

    def __init__(self, computer_color=Color.ORANGE, depth_to_use=10):
        self.computer_color = computer_color
        self.depth_to_use = depth_to_use

    def decide_move(self, game=CheckersGame()):
        if game.get_turn_of() is None or game.get_turn_of() != self.computer_color:
            raise Exception("Decision engine criteria not met")

        if len(game.turn_player_opts) == 1:
            move_chosen = game.get_possible_opts()[0]
            print(
                f"\n=================================\nOnly 1 option possible\n\n{move_chosen = }\n\n=================================\n"
            )
            return move_chosen

        print(
            "\n=================================\nNegamax has started\n\nProcessing .....\n"
        )
        start_time = time.time()

        move_chosen, value, max_depth_reached = self.negamax(
            game.get_game_state(),
            game.get_draw_criteria_log(),
            self.depth_to_use,
            -NegamaxDecisionEngine.ASSESSMENT_VALUE_MAX_AMPLITUDE,
            NegamaxDecisionEngine.ASSESSMENT_VALUE_MAX_AMPLITUDE,
            1,
        )

        time_elapsed = time.time() - start_time
        print(
            f"""
Finished in {time_elapsed} s

{move_chosen =}
{value = }
{max_depth_reached = }

=================================
        """
        )

        return move_chosen

    def negamax(
        self, game_state, draw_criteria_log, depth_to_use, alpha, beta, turn_of
    ):

        turn_of_color = (
            self.computer_color
            if turn_of == 1
            else (Color.BLUE if self.computer_color == Color.ORANGE else Color.ORANGE)
        )

        # check for draw criteria
        draw_criteria_count = 0
        for i in draw_criteria_log:
            if i[0] == turn_of_color and i[1] == game_state:
                draw_criteria_count += 1
        if draw_criteria_count >= 3:
            return None, 0, 0

        # check for win/lose criteria
        possible_next_moves = CheckersGame.get_color_poss_opts(
            turn_of_color, game_state
        )

        if len(possible_next_moves) == 0:
            return None, -NegamaxDecisionEngine.ASSESSMENT_VALUE_MAX_AMPLITUDE, 0

        # Check for depth criteria
        if depth_to_use < 1:
            return None, turn_of * self.assign_value(game_state), 0

        # Child node assessment
        value = -NegamaxDecisionEngine.ASSESSMENT_VALUE_MAX_AMPLITUDE
        move_chosen = None
        max_depth = 1
        for move in possible_next_moves:
            child_game_state = CheckersGame.get_outcome_of_move(
                [i.copy() for i in game_state], move
            )
            child_draw_criteria_log = []
            for i in draw_criteria_log:
                child_draw_criteria_log.append((i[0], [j.copy() for j in i[1]]))
            child_draw_criteria_log.append((turn_of_color, child_game_state))

            candidate_move_chosen, candidate_value, candidate_max_depth = self.negamax(
                child_game_state,
                child_draw_criteria_log,
                depth_to_use - 1,
                -beta,
                -alpha,
                -turn_of,
            )

            if candidate_max_depth + 1 > max_depth:
                max_depth = candidate_max_depth + 1

            if -candidate_value > value:
                value = -candidate_value
                move_chosen = move

            if value > alpha:
                alpha = value

            if alpha >= beta:
                break

        return move_chosen, value, max_depth

    # The simplest version of algorithm assigning values:
    #   number of your pieces (kings counts as two)
    #   minus number of opponent pieces (kings counts as two)
    # values in range <-ASSESSMENT_VALUE_MAX_AMPLITUDE, ASSESSMENT_VALUE_MAX_AMPLITUDE>
    def assign_value(self, game_state):

        if self.computer_color == Color.ORANGE:
            return np.sum(game_state)

        return -np.sum(game_state)
