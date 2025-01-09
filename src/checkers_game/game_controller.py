import numpy as np
from src.checkers_game.checkers_game import CheckersGame, Color, Status
from src.checkers_game.negamax import NegamaxDecisionEngine
from src.common.enums import (
    RobotGameReportItem,
    GameStateResult,
)
from src.common.utils import get_coord_from_tile_id


class GameController:
    def __init__(self, robot_color: Color, engine_depth: int = 3):
        self.game = CheckersGame()

        self.computer_color: Color = robot_color

        self.robot_move = None
        self.is_crowned = None

        self.decision_engine = NegamaxDecisionEngine(
            computer_color=self.computer_color, depth_to_use=engine_depth
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

    def update_game_state(
        self, board_state: np.ndarray, allow_different_robot_moves=False
    ) -> GameStateResult:
        is_robot_turn: bool = self.game.get_turn_of() == self.computer_color

        # Visual recognition doesn't recognise kings as different - so we must assume that kings are perceived as normal pieces by CV
        self_game_state = self.game.get_game_state()
        for i in range(0, len(self_game_state), 1):
            for j in range(0, len(self_game_state[i]), 1):
                if self_game_state[i][j] == -2:
                    self_game_state[i][j] = -1
                if self_game_state[i][j] == 2:
                    self_game_state[i][j] = 1

        print(f"{board_state=}")
        rotated_board_state = np.rot90(board_state, 2)

        # 1 - checking if game state hasn't changed
        # is_same_state = False
        # if np.array_equal(board_state, self_game_state) or np.array_equal(
        #     rotated_board_state, self_game_state
        # ):
        is_same_state = (
            True
            if np.array_equal(board_state, self_game_state)
            or np.array_equal(rotated_board_state, self_game_state)
            else False
        )
        if is_same_state:
            if is_robot_turn:
                if self.robot_move is None or self.is_crowned is None:
                    self.robot_move = self.decision_engine.decide_move(self.game)
                    x_tmp, y_tmp = get_coord_from_tile_id(self.robot_move[0])
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
                return GameStateResult.NO_ROBOT_MOVE
            return GameStateResult.NO_OPPONENT_MOVE

        # 2 - checking if move was permitted, and if yes what was the exact move
        is_permitted = False
        move_performed = None
        moves_allowed = self.game.get_possible_outcomes()

        for move_outcome in moves_allowed:
            # Visual recognition doesn't recognise kings as different - so we must assume that kings are perceived as normal pieces by CV
            for i in range(len(move_outcome[1])):
                for j in range(len(move_outcome[1][i])):
                    if move_outcome[1][i][j] == -2:
                        move_outcome[1][i][j] = -1
                    if move_outcome[1][i][j] == 2:
                        move_outcome[1][i][j] = 1

            if np.array_equal(board_state, move_outcome[1]) or np.array_equal(
                rotated_board_state, move_outcome[1]
            ):
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
                    return GameStateResult.VALID_RIGHT_ROBOT_MOVE
                if allow_different_robot_moves:
                    self.game.perform_move(move_performed)
                    self.robot_move = None
                    self.is_crowned = None
                return GameStateResult.VALID_WRONG_ROBOT_MOVE

            self.game.perform_move(move_performed)

            if self.game.get_status() == Status.IN_PROGRESS:
                self.robot_move = self.decision_engine.decide_move(self.game)
                x_tmp, y_tmp = get_coord_from_tile_id(self.robot_move[0])
                piece_moved = self.game.get_game_state()[x_tmp][y_tmp]
                if (
                    self.computer_color == Color.BLUE
                    and self.robot_move[-1] in [1, 2, 3, 4]
                    and piece_moved == -1
                ) or (
                    self.computer_color == Color.ORANGE
                    and self.robot_move[-1] in [29, 30, 31, 32]
                    and piece_moved == 1
                ):
                    self.is_crowned = True
                else:
                    self.is_crowned = False
            else:
                self.robot_move = None
                self.is_crowned = None

            return GameStateResult.VALID_OPPONENT_MOVE

        # 3 - informing about invalid move
        return (
            GameStateResult.INVALID_ROBOT_MOVE
            if is_robot_turn
            else GameStateResult.INVALID_OPPONENT_MOVE
        )
