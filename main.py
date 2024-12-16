import traceback
from src.GUI import game_window
from src.GUI.game_window import GameWindow
from src.GUI.init_window import ConfigurationWindow
from src.common.dataclasses import ColorConfig
from src.computer_vision.board_recognition.board import Board
from src.computer_vision.game_recognition import Game
import cv2


def main() -> None:
    config_window = ConfigurationWindow()
    config_window.run()

    camera_port = config_window.get_camera_port()
    color_config = config_window.get_config_colors_dict()
    color_config = ColorConfig(
        color_config["Orange"][::-1],
        color_config["Blue"][::-1],
        color_config["Black"][::-1],
        color_config["White"][::-1],
    )

    cap = cv2.VideoCapture(camera_port)
    game = Game(
        ColorConfig((219, 95, 33), (19, 99, 148), (45, 47, 36), (178, 188, 187))
    )

    while True:
        _, frame = cap.read()
        try:
            if game.update_game_state(frame):
                print("Game state changed")

            cv2.imshow("Game state", game.game_state_image)
            cv2.imshow("Frame", Board.detect_board(frame).frame)
        except Exception as e:
            print(e)
            print(traceback.format_exc())
        if cv2.waitKey(30) == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
