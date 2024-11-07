from checkers_game_and_decissions.checkers_game import CheckersGame, Color, Status
from checkers_game_and_decissions.negamax_decission_engine import (
    NegamaxDecisionEngine,
)
from checkers_game_and_decissions.enum_entities import RobotGameReportItem, UpdateGameStateResult
from checkers_game_and_decissions.utilities import get_coord_from_field_id

def rotate_2d_matrix_180_deg(matrix):
    new_matrix = []
    for c in range(len(matrix) - 1, -1, -1):
        tmp_col = []
        for i in range(len(matrix[c]) - 1, -1, -1):
            tmp_col.append(matrix[c][i])
        new_matrix.append(tmp_col)

    return new_matrix


class PVRobotController:

    def __init__(self):
        self.game = CheckersGame()

        print("==== Game Decission Engine Init ====")
        color_chosen = False
        choice = None
        while not color_chosen:
            print("Please input the color of the Robot Player: [b]lue/[o]range")

            choice = input()
            if choice == "b" or choice == "o":
                color_chosen = True

        print("====================================")

        if choice == "b":
            self.human_color = Color.ORANGE
        else:
            self.human_color = Color.BLUE

        self.computer_color = (
            Color.BLUE if self.human_color == Color.ORANGE else Color.ORANGE
        )
        self.robot_move = None
        self.is_crowned = None

        self.decision_engine = NegamaxDecisionEngine(
            computer_color=self.computer_color, depth_to_use=3
        )

    def report_state(self):
        report = {
            RobotGameReportItem.GAME_STATE: self.game.get_game_state(),
            RobotGameReportItem.POINTS: self.game.get_points(),
            RobotGameReportItem.STATUS: self.game.get_status(),
            RobotGameReportItem.WINNER: self.game.get_winning_player(),
            RobotGameReportItem.OPTIONS: self.game.get_possible_opts(),
            RobotGameReportItem.TURN_OF: self.game.get_turn_of(),
            RobotGameReportItem.ROBOT_COLOR: self.computer_color,
            RobotGameReportItem.ROBOT_MOVE: self.robot_move,
            RobotGameReportItem.IS_CROWNED: self.is_crowned,
        }

        return report

    def update_game_state(self, board_state, allow_different_robot_moves=False):

        # bool
        is_robot_turn = self.game.get_turn_of() == self.computer_color

        # Visual recognition doesn't recognise kings as different - so we must assume that kings are perceived as normal pieces by CV
        self_game_state = self.game.get_game_state()
        for i in range(0, len(self_game_state), 1):
            for j in range(0, len(self_game_state[i]), 1):
                if self_game_state[i][j] == -2:
                    self_game_state[i][j] = -1
                if self_game_state[i][j] == 2:
                    self_game_state[i][j] = 1

        rotated_board_state = rotate_2d_matrix_180_deg(board_state)

        # 1 - checking if game state hasn't changed
        is_same_state = False
        if board_state == self_game_state:
            is_same_state = True
        if rotated_board_state == self_game_state:
            is_same_state = True
        if is_same_state:
            if is_robot_turn:
                if self.robot_move is None or self.is_crowned is None:
                    self.robot_move = self.decision_engine.decide_move(self.game)
                    x_tmp, y_tmp = get_coord_from_field_id(self.robot_move[0])
                    piece_moved = self.game.get_game_state()[x_tmp][y_tmp]
                    if (
                        self.computer_color == Color.BLUE
                        and self.robot_move[len(self.robot_move) - 1] in [1, 2, 3, 4]
                        and piece_moved == -1
                    ) or (
                        self.computer_color == Color.ORANGE
                        and self.robot_move[len(self.robot_move) - 1]
                        in [29, 30, 31, 32]
                        and piece_moved == 1
                    ):
                        self.is_crowned = True
                    else:
                        self.is_crowned = False
                return UpdateGameStateResult.NO_ROBOT_MOVE
            else:
                return UpdateGameStateResult.NO_OPPONENT_MOVE

        # 2 - checking if move was permitted, and if yes what was the exact move
        is_permitted = False
        move_performed = None
        moves_allowed = self.game.get_possible_outcomes()

        for move_outcome in moves_allowed:
            # Visual recognition doesn't recognise kings as different - so we must assume that kings are perceived as normal pieces by CV
            for i in range(0, len(move_outcome[1]), 1):
                for j in range(0, len(move_outcome[1][i]), 1):
                    if move_outcome[1][i][j] == -2:
                        move_outcome[1][i][j] = -1
                    if move_outcome[1][i][j] == 2:
                        move_outcome[1][i][j] = 1

            if board_state == move_outcome[1]:
                is_permitted = True
                move_performed = move_outcome[0]
                break
            if rotated_board_state == move_outcome[1]:
                is_permitted = True
                move_performed = move_outcome[0]
                break

        # 2.5 - if is permitted then perform actions accordingly
        if is_permitted:
            if is_robot_turn:
                was_right_move = move_performed == self.robot_move

                if was_right_move:
                    self.game.perform_move(move_performed)
                    self.robot_move = None
                    self.is_crowned = None
                    return UpdateGameStateResult.VALID_RIGHT_ROBOT_MOVE
                else:
                    if allow_different_robot_moves:
                        self.game.perform_move(move_performed)
                        self.robot_move = None
                        self.is_crowned = None
                    return UpdateGameStateResult.VALID_WRONG_ROBOT_MOVE

            else:
                self.game.perform_move(move_performed)

                if self.game.get_status() == Status.IN_PROGRESS:
                    self.robot_move = self.decision_engine.decide_move(self.game)
                    x_tmp, y_tmp = get_coord_from_field_id(self.robot_move[0])
                    piece_moved = self.game.get_game_state()[x_tmp][y_tmp]
                    if (
                        self.computer_color == Color.BLUE
                        and self.robot_move[len(self.robot_move) - 1] in [1, 2, 3, 4]
                        and piece_moved == -1
                    ) or (
                        self.computer_color == Color.ORANGE
                        and self.robot_move[len(self.robot_move) - 1]
                        in [29, 30, 31, 32]
                        and piece_moved == 1
                    ):
                        self.is_crowned = True
                    else:
                        self.is_crowned = False
                else:
                    self.robot_move = None
                    self.is_crowned = None

                return UpdateGameStateResult.VALID_OPPONENT_MOVE

        # 3 - informing about invalid move
        if is_robot_turn:
            return UpdateGameStateResult.INVALID_ROBOT_MOVE

        return UpdateGameStateResult.INVALID_OPPONENT_MOVE

    def restart(self):
        self.game = CheckersGame()

    def get_log(self):
        return self.game.get_log()


# msc testing
if __name__ == "__main__":

    controller = PVRobotController()

    report = controller.report_state()

    for i in report:
        print(report[i])
