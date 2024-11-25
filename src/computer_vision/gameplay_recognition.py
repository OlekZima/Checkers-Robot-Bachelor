import cv2
import numpy as np

from src.computer_vision.game_board_recognition import Board
from src.computer_vision.checkers_recognition import Checkers, Color
from src.checkers_game_and_decissions.utilities import list_camera_ports, empty_function


class Game:
    def __init__(self, handle_capture=True, lack_of_trust_level=5):
        # Convention:
        # game state is 2d matrix -> list of columns
        # 1 represents orange, -1 represents blue
        # the orange are on the upper side
        # the game_state[0][0] is the upper left field
        # the game_state[7][7] is the bottom right field
        # the upper side is y = 0
        # the bottom side is y = 7

        if handle_capture:
            # Looking for available cameras
            working_ports = list_camera_ports()

            print("\nPlease select camera port by index")
            for i, p in enumerate(working_ports):
                print(f"[{i}]: {p}")

            port_idx = int(input())

            port = working_ports[port_idx]  # [0]
            # port = port_idx

            self.cap = cv2.VideoCapture()
            self.cap.open(port)
            self.cap.set(
                cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc("M", "J", "P", "G")
            )
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

            self.bgrs = []
            self.calibration_frame = None

            (
                self.orange_bgr,
                self.blue_bgr,
                self.dark_field_bgr,
                self.light_field_bgr,
            ) = self.calibrate_colors()

            cv2.namedWindow("Parameters - Board")
            cv2.resizeWindow("Parameters - Board", 640, 340)
            cv2.createTrackbar("Threshold1", "Parameters - Board", 140, 255, empty_function)
            cv2.createTrackbar("Threshold2", "Parameters - Board", 255, 255, empty_function)
            cv2.createTrackbar("Min_area", "Parameters - Board", 150, 600, empty_function)
            cv2.createTrackbar("Area_margin", "Parameters - Board", 500, 700, empty_function)
            cv2.createTrackbar("Kernel_size", "Parameters - Board", 5, 10, empty_function)
            cv2.createTrackbar("Approx_peri", "Parameters - Board", 3, 50, empty_function)
            cv2.createTrackbar("Px_dist", "Parameters - Board", 15, 100, empty_function)
            cv2.createTrackbar(
                "Color_dist_threshold", "Parameters - Board", 80, 200, empty_function
            )

            self.handle_capture = True

        else:
            self.handle_capture = False

        self.game_state = [
            [0, 1, 0, 0, 0, -1, 0, -1],
            [1, 0, 1, 0, 0, 0, -1, 0],
            [0, 1, 0, 0, 0, -1, 0, -1],
            [1, 0, 1, 0, 0, 0, -1, 0],
            [0, 1, 0, 0, 0, -1, 0, -1],
            [1, 0, 1, 0, 0, 0, -1, 0],
            [0, 1, 0, 0, 0, -1, 0, -1],
            [1, 0, 1, 0, 0, 0, -1, 0],
        ]

        self.game_state_log = [self.game_state]
        self.lack_of_trust_level = lack_of_trust_level

    @classmethod
    def build_game_state(cls, checkers, is_00_white:bool):
        game_state = [
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
        ]

        for c in checkers:
            if c.color == Color.ORANGE:
                game_state[c.pos[0]][c.pos[1]] = 1
            else:
                game_state[c.pos[0]][c.pos[1]] = -1

        if not is_00_white:
            game_state = cls.rotate_square_2D_matrix_right(game_state)

        return game_state

    def calibration_mouse_listener(self, event, x, y):
        if event == cv2.EVENT_LBUTTONUP:
            self.bgrs.append(self.calibration_frame[y][x])

    def calibrate_colors(self):
        self.bgrs = []
        cnt = 0
        texts = [
            "SELECT ORANGE CHECKER",
            "SELECT BLUE CHECKER",
            "SELECT DARK FIELD",
            "SELECT LIGHT FIELD",
        ]

        tmp = np.zeros((1, 1, 3), dtype=np.uint8)
        cv2.imshow("Calibration", tmp)

        cv2.setMouseCallback("Calibration", self.calibration_mouse_listener)

        while len(self.bgrs) < 4:
            success, img = self.cap.read()

            cv2.putText(
                img,
                texts[cnt],
                (int(img.shape[0] / 10), int(img.shape[1] / 2)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                3,
                cv2.LINE_AA,
            )

            img = cv2.resize(img, (0, 0), fx=0.8, fy=0.8)
            cv2.imshow("Calibration", img)
            self.calibration_frame = img

            cnt = len(self.bgrs)

            if cv2.waitKey(30) == ord("q"):  # & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()
        # cv2.destroyWindow("Calibration")

        return self.bgrs

    def present_visually(self):
        img = np.zeros((500, 500, 3), np.uint8)  # create black empty plane
        img[:, :] = (240, 240, 240)  # setting background

        is_dark = False
        for x in range(0, 8, 1):  # drawing fields
            for y in range(0, 8, 1):
                if is_dark:
                    cv2.rectangle(
                        img,
                        (x * 50 + 50, y * 50 + 50),
                        (x * 50 + 100, y * 50 + 100),
                        (0, 25, 80),
                        -1,
                    )
                else:
                    cv2.rectangle(
                        img,
                        (x * 50 + 50, y * 50 + 50),
                        (x * 50 + 100, y * 50 + 100),
                        (180, 225, 255),
                        -1,
                    )

                is_dark = not is_dark
            is_dark = not is_dark

        for i in range(0, 9, 1):
            cv2.line(
                img, [50 + i * 50, 50], [50 + i * 50, 450], (0, 0, 0), 3
            )  # drawing vertical lines
            cv2.line(
                img, [50, 50 + i * 50], [450, 50 + i * 50], (0, 0, 0), 3
            )  # drawing horizontal lines

        for x, _ in enumerate(self.game_state):  # drawing checkers
            for y, _ in enumerate(self.game_state[x]):
                if self.game_state[x][y] == 1:
                    cv2.circle(img, [x * 50 + 75, y * 50 + 75], 20, (50, 85, 220), -1)
                if self.game_state[x][y] == -1:
                    cv2.circle(img, [x * 50 + 75, y * 50 + 75], 20, (205, 105, 60), -1)

        return img

    def handle_next_frame(self, frame):
        img_res = frame.copy()

        t1 = cv2.getTrackbarPos("Threshold1", "Parameters - Board")
        t2 = cv2.getTrackbarPos("Threshold2", "Parameters - Board")
        kernel_size = cv2.getTrackbarPos("Kernel_size", "Parameters - Board")
        min_area = cv2.getTrackbarPos("Min_area", "Parameters - Board")
        area_margin = cv2.getTrackbarPos("Area_margin", "Parameters - Board")
        approx_peri_fraction = (
            float(cv2.getTrackbarPos("Approx_peri", "Parameters - Board")) / 100.0
        )
        px_dist_to_join = float(cv2.getTrackbarPos("Px_dist", "Parameters - Board"))
        color_dist_thresh = cv2.getTrackbarPos(
            "Color_dist_threshold", "Parameters - Board"
        )

        try:
            board = Board.detect_board(
                img_res,
                t1=t1,
                t2=t2,
                kernel=np.ones((kernel_size, kernel_size)),
                min_area=min_area,
                area_margin=area_margin,
                approx_peri_fraction=approx_peri_fraction,
                px_dist_to_join=px_dist_to_join,
            )

            Checkers.detect_checkers(
                board,
                frame,
                self.orange_bgr,
                self.blue_bgr,
                color_dist_thresh,
            )

            has_changed = self.challenge_game_state_change(
                Game.build_game_state(
                    Checkers.checkers,
                    is_00_white=board.is_00_white(
                        dark_field_bgr=self.dark_field_bgr,
                        light_field_bgr=self.light_field_bgr,
                        orange_bgr=self.orange_bgr,
                        green_bgr=self.blue_bgr,
                        color_dist_thresh=color_dist_thresh,
                    ),
                )
            )

        except Exception as e:
            # print("\n=-=-=--=-=-=-=-=-=-=-=-=-=-= Couldn't map board =-=-=--=-=-=-=-=-=-=-=-=-=-=\n")
            print(e)
            img_res = cv2.resize(img_res, (0, 0), fx=0.8, fy=0.8)
            cv2.imshow("RESULT", img_res)
            raise Exception("Couldn't map board")

        img_res = cv2.resize(img_res, (0, 0), fx=0.8, fy=0.8)
        cv2.imshow("RESULT", img_res)
        cv2.imshow("GAME STATE", self.present_visually())
        cv2.waitKey(1)
        return has_changed

    def capture_next_frame(self):
        if not self.handle_capture:
            success = False
        else:
            success, img = self.cap.read()

        if success:
            return img

        raise Exception("Failure during capturing frame or capture mode not selected")

    def challenge_game_state_change(self, game_state):
        if game_state is None:
            return False

        for log_entry in self.game_state_log:
            if log_entry != game_state:
                self.game_state_log = [game_state]
                # print("============NOT THE SAME=============")
                # print(l)
                # print(game_state)
                return False

        if len(self.game_state_log) + 1 >= self.lack_of_trust_level:
            self.game_state = game_state
            self.game_state_log = [game_state]
            # print("============UPDATED =============")
            return True

        self.game_state_log.append(game_state)
        # print("============SAME but need more =============")
        return False

    def get_fresh_game_state(self):
        new_frame = self.capture_next_frame()

        has_state_possibly_change = self.handle_next_frame(new_frame)

        return has_state_possibly_change, [i.copy() for i in self.game_state]


    @staticmethod
    def rotate_square_2D_matrix_right(matrix):
        new_matrix = []

        for _ in matrix[0]:
            new_matrix.append([])

        for x in range(0, len(matrix), 1):
            for y in range(0, len(matrix[x]), 1):
                new_matrix[y].append(matrix[x][len(matrix[x]) - y - 1])

        return new_matrix

