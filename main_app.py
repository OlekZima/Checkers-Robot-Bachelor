from checkers_game_and_decissions.pvrobot_game_controller import PVRobotController, UpdateGameStateResult
from checkers_game_and_decissions.enum_entities import RobotGameReportItem
from checkers_game_and_decissions.checkers_game import Status

from computer_vision.gameplay_recognition import Game
from robot_manipulation.calibration import Calibrator

from robot_manipulation.dobot_controller import DobotController
import cv2 as cv


def main():




    game = PVRobotController()

    print("Do you want to calibrate dobot (Y/N)?")
    is_correct = False
    user_input = None
    while not is_correct:
        user_input = input().upper()
        if user_input == "Y":
            is_correct = True
        elif user_input == "N":
            is_correct = True
        else:
            print("Please enter either Y or N")

    if user_input == "Y":
        Calibrator()


    dobot = DobotController(color = game.computer_color)

    board_recognition = Game(handle_capture = True, lack_of_trust_level = 5)

    buffer_clean_cnt = 0

    while True:

        if buffer_clean_cnt > 0:
            board_recognition.cap.read()
            buffer_clean_cnt -= 1
            if cv.waitKey(30) == ord("q"): #& 0xFF == ord("q"):
                break
            continue

        try:
            has_state_possibly_change, game_state = board_recognition.get_fresh_game_state()

        except Exception as e:
            #print(e)
            #print("Failed to recognise board")
            if cv.waitKey(30) == ord("q"): #& 0xFF == ord("q"):
                break
            continue

        if not has_state_possibly_change:
            if cv.waitKey(30) == ord("q"): #& 0xFF == ord("q"):
                break
            continue

        
        update_game_state_result = game.update_game_state(game_state, allow_different_robot_moves = False)

        if update_game_state_result in [
            UpdateGameStateResult.INVALID_OPPONENT_MOVE,
            UpdateGameStateResult.INVALID_ROBOT_MOVE
        ]:
            print(f"======\n{update_game_state_result}\nMove went wrong! Correct it!\n=========\n")
            
            if cv.waitKey(1500) == ord("q"): #& 0xFF == ord("q"):
                break
            continue

        if update_game_state_result == UpdateGameStateResult.VALID_WRONG_ROBOT_MOVE:
            print(f"======\n{update_game_state_result}\nNot the move selected! Correct it!\n=========\n")
            cv.waitKey(1500)
            continue

        game_state_report = game.report_state()

        if game_state_report[RobotGameReportItem.STATUS] != Status.IN_PROGRESS:
            cv.waitKey(30)
            print("====================== RESULTS ==========================")

            if  game_state_report[RobotGameReportItem.STATUS] == Status.DRAW:
                print("The match ended in DRAW")
            elif game_state_report[RobotGameReportItem.WINNER] == game_state_report[RobotGameReportItem.ROBOT_COLOR]:
                print("The winner is ROBOT!!!")
            else:
                print("The winner is HUMAN")

            print(f"=========================================================")
            break

        if game_state_report[RobotGameReportItem.TURN_OF] == game_state_report[RobotGameReportItem.ROBOT_COLOR]:
            print(f"======\n{update_game_state_result}\nAwaiting for robot move\n=========\n")
            dobot.perform_move(
                game_state_report[RobotGameReportItem.ROBOT_MOVE],
                is_crown= game_state_report[RobotGameReportItem.IS_CROWNED]
            )
            cv.waitKey(30)
            buffer_clean_cnt = 20
            continue

        print(f"======\n{update_game_state_result}\nAwaiting for opponent move\n=========\n")

        if cv.waitKey(30) == ord("q"): #& 0xFF == ord("q"):
            break

    cv.destroyAllWindows()


if __name__ == "__main__":

    #conda env -> robot_checkers

    main()
