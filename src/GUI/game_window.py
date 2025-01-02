import PySimpleGUI as sg
import cv2
import numpy as np
from pathlib import Path

from ..common.dataclasses import ColorConfig

from ..computer_vision.game_state_recognition import Game

from ..robot_manipulation.DobotController import DobotController

from ..checkers_game_and_decisions.pvrobot_game_controller import PVRobotController

from ..common.enum_entities import Color, GameStateResult, RobotGameReportItem, Status


class GameWindow:
    def __init__(
        self,
        robot_color: Color,
        robot_port: str,
        camera_port=0,
        color_config: ColorConfig = None,
    ) -> None:
        self._robot_color = robot_color
        self._robot_port = robot_port
        self._camera_port = camera_port
        self._config_colors = color_config

        self._cap = None

        self._recording = False

        # Initialize game components
        self._color_config = ColorConfig(
            (238, 96, 35),
            (45, 117, 168),
            (103, 109, 100),
            (209, 214, 208),
        )
        self._game = PVRobotController(Color.BLUE, 3)
        self._dobot = DobotController(Color.BLUE, Path("configs/guit_test_2.txt"), None)
        self._board_recognition = Game(self._color_config)
        self._board_image = None
        self._game_state_image = None

        self._layout = self._setup_main_layout()
        self._window = sg.Window(
            "Checkers Game", self._layout, resizable=False
        ).Finalize()

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
                sg.Graph(
                    canvas_size=(640, 480),
                    graph_bottom_left=(0, 0),
                    graph_top_right=(640, 480),
                    enable_events=True,
                    background_color="orange",
                    key="-Main_Camera_View-",
                ),
                sg.Output(size=(40, 20), key="-OUTPUT-"),
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
                sg.Graph(
                    canvas_size=(640, 480),
                    graph_bottom_left=(0, 0),
                    graph_top_right=(640, 480),
                    background_color="red",
                    key="-Game_State_View-",
                ),
                sg.Graph(
                    canvas_size=(640, 480),
                    graph_bottom_left=(0, 0),
                    graph_top_right=(640, 480),
                    background_color="black",
                    key="-Board_View-",
                ),
            ],
            [
                sg.Graph(
                    canvas_size=(640, 480),
                    graph_bottom_left=(0, 0),
                    graph_top_right=(640, 480),
                    background_color="white",
                    key="-Camera_View-",
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
        self._window[graph_key].delete_figure(graph_key)
        self._window[graph_key].draw_image(data=imgbytes, location=(0, 480))

    def run(self):
        self._recording = True
        self._cap = cv2.VideoCapture(self._camera_port)
        # tmp = 0

        # Get initial board image
        self._board_image = self._board_recognition.get_board_image()

        while True:
            event, values = self._window.read(20)

            if event in (sg.WIN_CLOSED, "Cancel"):
                break

            ret, image = self._cap.read()
            if not ret:
                continue

            # if tmp > 0:
            #     tmp -= 1
            #     continue

            # Update main camera view
            self._update_graph(image, "-Main_Camera_View-")

            try:
                # Process game state
                game_state = self._board_recognition.update_game_state(image)
                update_game_state_result = self._game.update_game_state(game_state)

                # Update game state view
                self._game_state_image = self._board_recognition.get_game_state_image()
                self._update_graph(self._game_state_image, "-Game_State_View-")

                # Update board view
                self._update_graph(self._board_image, "-Board_View-")

                # Handle game state results
                if update_game_state_result in (
                    GameStateResult.INVALID_OPPONENT_MOVE,
                    GameStateResult.INVALID_ROBOT_MOVE,
                ):
                    self._window["-MOVE_STATUS-"].update(
                        "Invalid move! Please correct it."
                    )
                    continue

                if update_game_state_result == GameStateResult.VALID_WRONG_ROBOT_MOVE:
                    self._window["-MOVE_STATUS-"].update(
                        "Wrong robot move! Please correct it."
                    )
                    continue

                game_state_report = self._game.report_state()

                # Check game end conditions
                if game_state_report[RobotGameReportItem.STATUS] != Status.IN_PROGRESS:
                    if game_state_report[RobotGameReportItem.STATUS] == Status.DRAW:
                        self._window["-MOVE_STATUS-"].update("Game Over - DRAW!")
                    elif game_state_report[RobotGameReportItem.WINNER] == Color.BLUE:
                        self._window["-MOVE_STATUS-"].update("Game Over - ROBOT WON!")
                    else:
                        self._window["-MOVE_STATUS-"].update(
                            "Game Over - OPPONENT WON!"
                        )
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
                    # tmp = 20
                else:
                    self._window["-MOVE_STATUS-"].update("Player's turn...")

            except Exception as e:
                print(f"Error: {e}")
                continue

        if self._cap:
            self._cap.release()
        self._window.close()


if __name__ == "__main__":
    # Initialize and run the game window
    game_window = GameWindow(
        robot_color="blue",
        robot_port="COM3",
        camera_port=2,
    )
    game_window.run()
