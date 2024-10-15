from checkers_game_and_decissions.checkers_game import CheckersGame, Color, Status
from checkers_game_and_decissions.decission_engines.poc_decission_engine import POCDecissionEngine
from checkers_game_and_decissions.decission_engines.negamax_decission_engine import NegamaxDecissionEngine
import threading
import time
from checkers_game_and_decissions.report_item import ReportItem

class ComputerMoveThread(threading.Thread):
    def __init__(self, controller, delay):
        threading.Thread.__init__(self)
        self.controller = controller
        self.delay = delay

    def run(self):
        self.controller.computer_perform_move(delay=self.delay)


class PVCController:

    def __init__(self, human_color = Color.GREEN):
        self.game = CheckersGame()
        self.human_color = human_color
        self.computer_color = Color.GREEN if human_color == Color.RED else Color.RED
        self.decission_engine = NegamaxDecissionEngine(computer_color = self.computer_color, depth_to_use = 10)
        self.initial_computer_move = False
        if human_color == Color.RED:
            self.initial_computer_move = True

    def report_state(self):
        report = {
            ReportItem.GAME_STATE: self.game.get_game_state(),
            ReportItem.POINTS: self.game.get_points(),
            ReportItem.STATUS: self.game.get_status(),
            ReportItem.WINNER: self.game.get_winning_player(),
            ReportItem.OPTIONS: self.game.get_possible_opts(),
            ReportItem.TURN_OF: self.game.get_turn_of()
        }

        if self.initial_computer_move:
            thread = ComputerMoveThread(self, delay = 3)
            thread.start()
            self.initial_computer_move = False

        return report

    def perform_move(self, sequence):
        status =  self.game.perform_move(sequence)

        thread = ComputerMoveThread(self, delay = 3)
        thread.start()

        return status

    def computer_perform_move(self, delay = 1):
        time.sleep(delay)

        try:
            move_sequence = self.decission_engine.decide_move(self.game)
        except Exception as e:
            print(str(e))
            return

        self.game.perform_move(move_sequence)
    
    def restart(self):
        self.game = CheckersGame()

    def get_log(self):
        return self.game.get_log()