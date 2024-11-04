from checkers_game_and_decissions.checkers_game import CheckersGame
from checkers_game_and_decissions.enum_entities import Color
import random


class POCDecissionEngine:

    def __init__(self, computer_color=Color.ORANGE):
        self.computer_color = computer_color

    def decide_move(self, game=CheckersGame()):
        if game.get_turn_of() == None or game.get_turn_of() != self.computer_color:
            raise Exception("Decission engine criteria not met")

        opts = (
            game.get_possible_opts()
        )  # As of POC decission engine just takes a random decission

        random_opt_id = random.randint(0, len(opts) - 1)

        return opts[random_opt_id]
