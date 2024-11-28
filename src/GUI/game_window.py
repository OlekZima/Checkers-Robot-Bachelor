import PySimpleGUI as sg
import cv2


class GameWindow:
    def __init__(self, robot_color, robot_port, camera_port=0) -> None:
        self.robot_color = robot_color
        self.robot_port = robot_port
        self.camera_port = camera_port
        self._cap = None

        self._frame_main = None
        self._frame_vertices = None
        self._frame_game_mask = None

        self._image_id_main = None
        self._image_id_vertices = None
        self._image_id_game_mask = None

        self._recording = False

        self._layout = [
            [
                sg.TabGroup(
                    [
                        [sg.Tab("Game", self._setup_main_game_layout())],
                        [
                            sg.Tab(
                                "Additional views",
                                self._setup_additional_views_layout(),
                            )
                        ],
                    ]
                )
            ]
        ]

        self._window = sg.Window("Game Window", self._layout, resizable=False)

    def _setup_main_game_layout(self) -> list[sg.Element]:
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
                sg.Multiline("Default text"),
            ],
            [
                sg.Image(size=(200, 200), background_color="blue"),
                sg.Text("Move is"),
            ],
        ]
        return layout

    def _setup_additional_views_layout(self) -> list[sg.Element]:
        layout = [
            [
                sg.Graph(
                    canvas_size=(640, 480),
                    graph_bottom_left=(0, 0),
                    graph_top_right=(640, 480),
                    background_color="white",
                    key="-Vertices_View-",
                ),
                sg.Graph(
                    canvas_size=(640, 480),
                    graph_bottom_left=(0, 0),
                    graph_top_right=(640, 480),
                    background_color="black",
                    key="-Original_View-",
                ),
            ],
            [
                sg.Graph(
                    canvas_size=(640, 480),
                    graph_bottom_left=(0, 0),
                    graph_top_right=(640, 480),
                    background_color="red",
                    key="-Game_State_View-",
                ),
                sg.Column(
                    [
                        [sg.Slider((0, 10), orientation="horizontal")],
                        [sg.Slider((0, 10), orientation="horizontal")],
                        [sg.Slider((0, 10), orientation="horizontal")],
                        [sg.Slider((0, 10), orientation="horizontal")],
                    ]
                ),
            ],
        ]
        return layout

    def run(self):
        self._recording = True
        self._cap = cv2.VideoCapture(self.camera_port)
        while True:
            event, values = self._window.read(10)
            ret, frame = self._cap.read()

            if event in [sg.WIN_CLOSED, "Cancel"]:
                break

            if self._cap is not None and self._cap.isOpened():
                if ret:
                    imgbytes = cv2.imencode(".png", frame)[1].tobytes()
                    if self._image_id_main:
                        self._window["-Main_Camera_View-"].delete_figure(
                            self._image_id_main
                        )
                    self._image_id_main = self._window["-Main_Camera_View-"].draw_image(
                        data=imgbytes, location=(0, 480)
                    )

            if self._cap is not None and self._cap.isOpened():
                if ret:
                    imgbytes = cv2.imencode(".png", frame)[1].tobytes()
                    if self._image_id_vertices:
                        self._window["-Vertices_View-"].delete_figure(
                            self._image_id_vertices
                        )
                    self._image_id_vertices = self._window[
                        "-Vertices_View-"
                    ].draw_image(data=imgbytes, location=(0, 480))

            if self._cap is not None and self._cap.isOpened():
                if ret:
                    imgbytes = cv2.imencode(".png", frame)[1].tobytes()
                    if self._image_id_game_mask:
                        self._window["-Game_State_View-"].delete_figure(
                            self._image_id_game_mask
                        )
                    self._image_id_game_mask = self._window[
                        "-Game_State_View-"
                    ].draw_image(data=imgbytes, location=(0, 480))

            if self._cap is not None and self._cap.isOpened():
                if ret:
                    imgbytes = cv2.imencode(".png", frame)[1].tobytes()
                    if self._image_id_game_mask:
                        self._window["-Original_View-"].delete_figure(
                            self._image_id_game_mask
                        )
                    self._image_id_game_mask = self._window["-Original_View-"].draw_image(
                        data=imgbytes, location=(0, 480)
                    )

        if self._cap:
            self._cap.release()
        self._window.close()
