from checkers_game_and_decissions.checkers_game import CheckersGame
from checkers_game_and_decissions.report_item import ReportItem


class PVPController:

    def __init__(self):
        self.game = CheckersGame()

    def report_state(self):
        report = {
            ReportItem.GAME_STATE: self.game.get_game_state(),
            ReportItem.POINTS: self.game.get_points(),
            ReportItem.STATUS: self.game.get_status(),
            ReportItem.WINNER: self.game.get_winning_player(),
            ReportItem.OPTIONS: self.game.get_possible_opts(),
            ReportItem.TURN_OF: self.game.get_turn_of()
        }

        return report

    def perform_move(self, sequence):
        return self.game.perform_move(sequence)

    def restart(self):
        self.game = CheckersGame()

    def get_log(self):
        return self.game.get_log()