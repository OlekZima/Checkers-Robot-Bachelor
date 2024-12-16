from src.checkers_game_and_decisions.pvrobot_game_controller import (
    PVRobotController,
    GameStateResult,
)
from src.common.enum_entities import RobotGameReportItem
from src.checkers_game_and_decisions.checkers_game import Status
from src.computer_vision.gameplay_recognition import Game
from src.robot_manipulation.DobotController import DobotController
import cv2


def main():
    game = PVRobotController()

    dobot = DobotController(color=game.computer_color)

    board_recognition = Game(handle_capture=True, lack_of_trust_level=5)

    buffer_clean_cnt = 0

    while True:

        if buffer_clean_cnt > 0:
            board_recognition.cap.read()
            buffer_clean_cnt -= 1
            if cv2.waitKey(30) == ord("q"):  # & 0xFF == ord("q"):
                break
            continue

        try:
            has_state_possibly_change, game_state = (
                board_recognition.get_fresh_game_state()
            )

        except Exception as e:
            # print(e)
            # print("Failed to recognise board")
            if cv2.waitKey(30) == ord("q"):  # & 0xFF == ord("q"):
                break
            continue

        if not has_state_possibly_change:
            if cv2.waitKey(30) == ord("q"):  # & 0xFF == ord("q"):
                break
            continue

        update_game_state_result = game.update_game_state(
            game_state, allow_different_robot_moves=False
        )

        if update_game_state_result in [
            GameStateResult.INVALID_OPPONENT_MOVE,
            GameStateResult.INVALID_ROBOT_MOVE,
        ]:
            print(
                f"======\n{update_game_state_result}\nMove went wrong! Correct it!\n=========\n"
            )

            if cv2.waitKey(1500) == ord("q"):  # & 0xFF == ord("q"):
                break
            continue

        if update_game_state_result == GameStateResult.VALID_WRONG_ROBOT_MOVE:
            print(
                f"======\n{update_game_state_result}\nNot the move selected! Correct it!\n=======\n"
            )
            cv2.waitKey(1500)
            continue

        game_state_report = game.report_state()

        if game_state_report[RobotGameReportItem.STATUS] != Status.IN_PROGRESS:
            cv2.waitKey(30)
            print("====================== RESULTS ==========================")

            if game_state_report[RobotGameReportItem.STATUS] == Status.DRAW:
                print("The match ended in DRAW")
            elif (
                game_state_report[RobotGameReportItem.WINNER]
                == game_state_report[RobotGameReportItem.ROBOT_COLOR]
            ):
                print("The winner is ROBOT!!!")
            else:
                print("The winner is HUMAN")

            print("=========================================================")
            break

        if (
            game_state_report[RobotGameReportItem.TURN_OF]
            == game_state_report[RobotGameReportItem.ROBOT_COLOR]
        ):
            print(
                f"======\n{update_game_state_result}\nAwaiting for robot move\n=========\n"
            )
            dobot.perform_move(
                game_state_report[RobotGameReportItem.ROBOT_MOVE],
                is_crown=game_state_report[RobotGameReportItem.IS_CROWNED],
            )
            cv2.waitKey(30)
            buffer_clean_cnt = 20
            continue

        print(
            f"======\n{update_game_state_result}\nAwaiting for opponent move\n=========\n"
        )

        if cv2.waitKey(30) == ord("q"):  # & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    # conda env -> robot_checkers

    main()
