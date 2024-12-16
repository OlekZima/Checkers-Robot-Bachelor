import traceback
from typing import List, Optional

import cv2
import numpy as np
from src.common.dataclasses import ColorConfig, RecognitionConfig
from src.common.enum_entities import Color
from src.common.exceptions import BoardDetectionError
from src.computer_vision.board_recognition.board import Board
from src.computer_vision.checkers_recognition import Checkers


class Game:
    def __init__(
        self,
        colors: ColorConfig,
        lack_of_trust_level: int = 5,
        recognition_config: Optional[RecognitionConfig] = None,
    ) -> None:
        self.colors = colors
        self.lack_of_trust_level = lack_of_trust_level

        self.game_state = self._create_initial_game_state()
        self.game_state_log: List[np.ndarray] = [self.game_state]
        self.recognition_config = (
            recognition_config
            if recognition_config is not None
            else RecognitionConfig()
        )
        self.game_state_image: np.ndarray = np.array([])

    @staticmethod
    def _create_initial_game_state() -> np.ndarray:
        return np.array(
            [
                [0, 1, 0, 0, 0, -1, 0, -1],
                [1, 0, 1, 0, 0, 0, -1, 0],
                [0, 1, 0, 0, 0, -1, 0, -1],
                [1, 0, 1, 0, 0, 0, -1, 0],
                [0, 1, 0, 0, 0, -1, 0, -1],
                [1, 0, 1, 0, 0, 0, -1, 0],
                [0, 1, 0, 0, 0, -1, 0, -1],
                [1, 0, 1, 0, 0, 0, -1, 0],
            ]
        )

    @staticmethod
    def _create_empty_game_state() -> np.ndarray:
        return np.zeros((8, 8), dtype=int)

    @classmethod
    def build_game_state(
        cls, checkers: List[Checkers], is_00_white: bool
    ) -> np.ndarray:
        state = cls._create_empty_game_state()

        for checker in checkers:
            state[checker.pos[0]][checker.pos[1]] = (
                1 if checker.color == Color.ORANGE else -1
            )

        if not is_00_white:
            state = cls.rotate_matrix_clockwise(state)

        return state

    def update_game_log(self, game_state: np.ndarray) -> bool:
        for log in self.game_state_log:
            if np.array_equal(log, game_state):
                self.game_state_log = [game_state]
                return False

        if len(self.game_state_log) + 1 >= self.lack_of_trust_level:
            self.game_state = game_state
            self.game_state_log = [game_state]
            return True

        self.game_state_log.append(game_state)
        return False

    def update_game_state(self, image: np.ndarray):
        image_copy1 = image.copy()
        image_copy2 = image.copy()
        has_changed = False
        try:
            board = Board.detect_board(image_copy1)

            Checkers.detect_checkers(
                board, image_copy2, self.colors.orange, self.colors.blue
            )

            new_game_state = self.build_game_state(
                Checkers.checkers, board.is_00_white(self.colors)
            )

            has_changed = self.update_game_log(new_game_state)
        except Exception as e:
            print(e)

        self.update_game_state_image()
        return has_changed

    def update_game_state_image(self) -> np.ndarray:
        img = np.zeros((500, 500, 3), np.uint8)  # create black empty plane
        img[:, :] = (240, 240, 240)  # setting background

        is_dark = False
        for x in range(0, 8, 1):  # drawing fields
            for y in range(0, 8, 1):
                cv2.rectangle(
                    img,
                    (x * 50 + 50, y * 50 + 50),
                    (x * 50 + 100, y * 50 + 100),
                    (0, 25, 80) if is_dark else (180, 225, 225),
                    -1,
                )

                is_dark = not is_dark
            is_dark = not is_dark

        for i in range(0, 9, 1):
            # drawing vertical lines
            cv2.line(img, [50 + i * 50, 50], [50 + i * 50, 450], (0, 0, 0), 3)

            # drawing horizontal lines
            cv2.line(img, [50, 50 + i * 50], [450, 50 + i * 50], (0, 0, 0), 3)

        for x, _ in enumerate(self.game_state):  # drawing checkers
            for y, _ in enumerate(self.game_state[x]):
                color = (50, 85, 220) if self.game_state[x][y] == 1 else (205, 105, 60)
                cv2.circle(img, [x * 50 + 75, y * 50 + 75], 20, color, -1)

        self.game_state_image = img.copy()

    @staticmethod
    def rotate_matrix_clockwise(matrix: np.ndarray) -> np.ndarray:
        return np.rot90(matrix, 1)


if __name__ == "__main__":
    camera_port = 0
    cap = cv2.VideoCapture(camera_port)
    game = Game(
        ColorConfig((219, 95, 33), (19, 99, 148), (45, 47, 36), (178, 188, 187))
    )

    while True:
        ret, frame = cap.read()
        try:
            if game.update_game_state(frame):
                print("Game state changed")

            cv2.imshow("Game state", game.game_state_image)
            cv2.imshow("Frame", Board.detect_board(frame).frame)

            print(f"{Checkers.checkers=}")
        except Exception as e:
            print(e)
            print(traceback.format_exc())
        if cv2.waitKey(30) == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
