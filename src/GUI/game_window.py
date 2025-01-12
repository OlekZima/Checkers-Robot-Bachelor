from memory_profiler import profile
import PySimpleGUI as sg
import cv2
import numpy as np

from src.common.utils import CONFIG_PATH

from src.common.configs import ColorConfig

from src.computer_vision.board_recognition.contours import ContourProcessor
from src.computer_vision.game_state_recognition import GameState

from src.robot_manipulation.dobot_controller import DobotController

from src.checkers_game.game_controller import GameController

from src.common.enums import Color, GameStateResult, RobotGameReportItem, Status


class GameWindow:
    def __init__(
        self,
        robot_color: Color,
        robot_port: str,
        camera_port: int,
        color_config: ColorConfig,
        config_name: str,
        depth_of_engine: int = 3,
    ) -> None:
        self._camera_port = camera_port

        self._cap = cv2.VideoCapture(self._camera_port)

        self._game = GameController(robot_color, depth_of_engine)
        self._dobot = DobotController(robot_color, CONFIG_PATH / config_name, robot_port)
        self._device = self._dobot.device
        self._board_recognition = GameState(color_config)

        # self._board_image = None
        # self._game_state_image = None

        self._layout = self._setup_main_layout()
        self._window = sg.Window("Checkers Game", self._layout, resizable=False).Finalize()

    @staticmethod
    def _setup_main_layout() -> list[sg.Element]:
        layout = [
            [
                sg.TabGroup(
                    [
                        [
                            sg.Tab("Game", GameWindow._setup_main_game_layout()),
                        ],
                        [
                            sg.Tab(
                                "Additional views",
                                GameWindow._setup_additional_views_layout(),
                            )
                        ],
                    ]
                )
            ]
        ]
        return layout

    @staticmethod
    def _setup_main_game_layout() -> list[sg.Element]:
        layout = [
            [
                sg.Image(
                    enable_events=True,
                    size=(640, 480),
                    background_color="orange",
                    key="-Main_Camera_View-",
                ),
                sg.Output(size=(80, 50), key="-OUTPUT-"),
            ],
            [
                sg.Image(size=(200, 200), background_color="blue", key="-MOVE_IMAGE-"),
                sg.Text("", key="-MOVE_STATUS-"),
            ],
        ]
        return layout

    @staticmethod
    def _setup_additional_views_layout() -> list[sg.Element]:
        layout = [
            [
                sg.Image(
                    background_color="red",
                    size=(640, 480),
                    key="-Dilate_View-",
                ),
                sg.Image(
                    background_color="black",
                    size=(640, 480),
                    key="-Board_View-",
                ),
            ],
            [
                sg.Image(
                    background_color="white",
                    size=(500, 500),
                    key="-Game_State_View-",
                ),
                sg.Column(
                    [
                        [sg.Text("Kernel size")],
                        [
                            sg.Slider(
                                (0, 10),
                                orientation="horizontal",
                                key="-Kernel_size_slider-",
                            )
                        ],
                        [sg.Slider((0, 10), orientation="horizontal")],
                        [sg.Slider((0, 10), orientation="horizontal")],
                        [sg.Slider((0, 10), orientation="horizontal")],
                    ]
                ),
            ],
        ]
        return layout

    def _update_graph(self, frame: np.ndarray, graph_key: str) -> None:
        if frame is None or frame.size == 0:
            return
        imgbytes = cv2.imencode(".png", frame)[1].tobytes()
        self._window[graph_key].update(imgbytes)
        del imgbytes
        del frame

    @profile
    def run(self):
        frame_skip = 20

        while True:
            event, values = self._window.read(20)

            if event in (sg.WIN_CLOSED, "Cancel"):
                break

            ret, image = self._cap.read()
            if not ret:
                continue

            if frame_skip > 0:
                frame_skip -= 1
                continue

            # Update main camera view
            self._update_graph(image, "-Main_Camera_View-")

            try:
                # Process game state
                _, game_state = self._board_recognition.update_game_state(image)
                update_game_state_result = self._game.update_game_state(game_state)

                # Update game state view
                self._game_state_image = self._board_recognition.get_game_state_image()
                self._update_graph(self._game_state_image, "-Game_State_View-")

                # Update board view
                self._board_image = self._board_recognition.get_board_image()
                self._update_graph(self._board_image, "-Board_View-")

                dilate_image = ContourProcessor.image_dil
                self._update_graph(dilate_image, "-Dilate_View-")

                # Handle game state results
                if update_game_state_result in (
                    GameStateResult.INVALID_OPPONENT_MOVE,
                    GameStateResult.INVALID_ROBOT_MOVE,
                ):
                    self._window["-MOVE_STATUS-"].update("Invalid move! Please correct it.")
                    continue

                if update_game_state_result == GameStateResult.VALID_WRONG_ROBOT_MOVE:
                    self._window["-MOVE_STATUS-"].update("Wrong robot move! Please correct it.")
                    continue

                game_state_report = self._game.report_state()

                # Check game end conditions
                if game_state_report[RobotGameReportItem.STATUS] != Status.IN_PROGRESS:
                    if game_state_report[RobotGameReportItem.STATUS] == Status.DRAW:
                        self._window["-MOVE_STATUS-"].update("Game Over - DRAW!")
                    elif game_state_report[RobotGameReportItem.WINNER] == Color.BLUE:
                        self._window["-MOVE_STATUS-"].update("Game Over - ROBOT WON!")
                    else:
                        self._window["-MOVE_STATUS-"].update("Game Over - OPPONENT WON!")
                    break

                # Handle turns
                if (
                    game_state_report[RobotGameReportItem.TURN_OF]
                    == game_state_report[RobotGameReportItem.ROBOT_COLOR]
                ):
                    self._window["-MOVE_STATUS-"].update("Robot's turn...")
                    self._dobot.perform_move(
                        game_state_report[RobotGameReportItem.ROBOT_MOVE],
                        is_crown=game_state_report[RobotGameReportItem.IS_CROWNED],
                    )
                    frame_skip = 20
                else:
                    self._window["-MOVE_STATUS-"].update("Player's turn...")

            except Exception as e:
                print(f"Error: {e}")
                continue

        cv2.destroyAllWindows()
        self._cap.release()
        self._window.close()


if __name__ == "__main__":
    color_config = ColorConfig(
        {
            "orange": (220, 70, 0),
            "blue": (42, 113, 157),
            "black": (107, 108, 101),
            "white": (198, 205, 203),
        }
    )

    game_window = GameWindow(Color.ORANGE, "/dev/ttyUSB0", 2, color_config, "guit_test_2.txt")
    game_window.run()
