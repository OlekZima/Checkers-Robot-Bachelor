from pathlib import Path
import cv2
from src.GUI.init_window import ConfigurationWindow
from src.checkers_game_and_decisions.pvrobot_game_controller import PVRobotController
from src.common.dataclasses import ColorConfig
from src.common.enum_entities import Color, GameStateResult, RobotGameReportItem, Status
from src.computer_vision.game_state_recognition import Game
from src.robot_manipulation.DobotController import DobotController


class Checkers:
    @staticmethod
    def start():
        # config_window = ConfigurationWindow()
        # config_window.run()

        # camera_port = config_window.get_camera_port()
        # robot_port = config_window.get_robot_port()
        # color_dict = config_window.get_config_colors_dict()
        # robot_color = config_window.get_robot_color()
        # config_path = config_window.get_configuration_file_path()
        # difficulty_level = config_window.get_difficulty_level()

        color_config = ColorConfig(
            (238, 96, 35),
            (45, 117, 168),
            (103, 109, 100),
            (209, 214, 208),
        )

        game = PVRobotController(Color.BLUE, 3)

        dobot = DobotController(Color.BLUE, Path("configs/guit_test_2.txt"), None)

        board_recognition = Game(color_config)

        cap = cv2.VideoCapture(2)
        tmp = 0
        while True:
            ret, image = cap.read()
            if not ret:
                break

            if tmp > 0:
                tmp -= 1
                continue

            try:
                _, game_state = board_recognition.update_game_state(image)
            except Exception as e:
                print(e)
                continue

            update_game_state_result = game.update_game_state(game_state)

            cv2.imshow("Game state", board_recognition.get_game_state_image())

            if update_game_state_result in (
                GameStateResult.INVALID_OPPONENT_MOVE,
                GameStateResult.INVALID_ROBOT_MOVE,
            ):
                print(
                    f"======\n{update_game_state_result}\nMove went wrong! Correct it!\n=========\n"
                )
                continue

            if update_game_state_result == GameStateResult.VALID_WRONG_ROBOT_MOVE:
                print(
                    f"======\n{update_game_state_result}\nNot the move selected! Correct it!\n=======\n"
                )
                continue

            game_state_report = game.report_state()

            if game_state_report[RobotGameReportItem.STATUS] != Status.IN_PROGRESS:
                print("RESULTS")

                if game_state_report[RobotGameReportItem.STATUS] == Status.DRAW:
                    print("DRAW")
                elif game_state_report[RobotGameReportItem.WINNER] == Color.BLUE:
                    print("ROBOT WON")
                else:
                    print("OPPONENT WON")
                break

            if (
                game_state_report[RobotGameReportItem.TURN_OF]
                == game_state_report[RobotGameReportItem.ROBOT_COLOR]
            ):
                print("Waiting for robot move")
                dobot.perform_move(
                    game_state_report[RobotGameReportItem.ROBOT_MOVE],
                    is_crown=game_state_report[RobotGameReportItem.IS_CROWNED],
                )
                cv2.waitKey(30)
                tmp = 20
                continue

            print("Waiting for player move")

            if cv2.waitKey(30) == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    Checkers.start()
