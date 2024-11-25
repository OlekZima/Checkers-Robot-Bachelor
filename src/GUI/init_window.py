import PySimpleGUI as sg
from serial.tools import list_ports
import cv2
from src.computer_vision.gameplay_recognition import list_camera_ports


class ConfigurationWindow:
    def __init__(self) -> None:
        self._selected_color = None

        self._recording = False
        self._robot_port = None
        self._camera_port = None
        self._cap = None
        self._frame = None
        self._image_id = None

        self._selected_config_color = None

        self._configuration_colors: dict[str, tuple[int, int, int]] = {
            "Orange": (0, 0, 0),
            "Blue": (0, 0, 0),
            "Black": (0, 0, 0),
            "White": (0, 0, 0),
        }

        self._window = sg.Window(
            "Configuration", self._setup_main_layout(), resizable=False
        )

    def get_robot_port(self) -> str:
        return self._robot_port if self._robot_port is not None else None

    def get_camera_port(self) -> int:
        return self._camera_port if self._camera_port is not None else None

    def get_config_colors_dict(self) -> dict[str, tuple[int, int, int]]:
        return self._configuration_colors

    @staticmethod
    def _setup_main_layout() -> list[sg.Element]:
        layout: list[sg.Element] = [
            [
                sg.Text(
                    "Checkers Robot Configurattion",
                    justification="center",
                    expand_x=True,
                )
            ],
            [
                sg.TabGroup(
                    [
                        [
                            sg.Tab(
                                "Color Selection",
                                layout=ConfigurationWindow._setup_color_selection(),
                                key="-Color_Selection-",
                            ),
                            sg.Tab(
                                "Port Selection",
                                layout=ConfigurationWindow._setup_port_selection(),
                                key="-Port_Selection-",
                                visible=False,
                            ),
                            sg.Tab(
                                "Color Configuration",
                                layout=ConfigurationWindow._setup_color_configuration(),
                                key="-Color_Configuration-",
                                visible=False,
                            ),
                        ]
                    ],
                    expand_x=True,
                    enable_events=True,
                    key="-TABGROUP-",
                )
            ],
        ]
        return layout

    @staticmethod
    def _setup_color_selection() -> list[sg.Element]:
        layout = [
            [sg.VPush()],
            [sg.Text("Select Robot's color", justification="center", expand_x=True)],
            [
                sg.Push(),
                sg.Button(
                    image_filename="assets/checkers_img/orange.png",
                    key="-Select_Orange-",
                ),
                sg.Button(
                    image_filename="assets/checkers_img/blue.png", key="-Select_Blue-"
                ),
                sg.Push(),
            ],
            [
                sg.Text(
                    "Selected Color for robot is: None",
                    key="-Selected_Color-",
                    justification="center",
                    expand_x=True,
                )
            ],
            [sg.VPush()],
        ]

        return layout

    @staticmethod
    def _setup_port_selection() -> list[sg.Element]:
        layout = [
            [sg.VPush()],
            [
                sg.Text(
                    text="Select port for the robot:",
                    expand_x=True,
                    justification="center",
                ),
                sg.Text(
                    text="Select port for the camera:",
                    expand_x=True,
                    justification="center",
                ),
            ],
            [
                sg.OptionMenu(
                    values=list_ports.comports(),
                    key="-Robot_Port-",
                    expand_x=True,
                    enable_events=True,
                ),
                sg.OptionMenu(
                    values=list_camera_ports(),
                    key="-Camera_Port-",
                    expand_x=True,
                    enable_events=True,
                ),
            ],
            [sg.VPush()],
        ]
        return layout

    @staticmethod
    def _setup_color_configuration() -> list[sg.Element]:
        layout: list = [
            [
                sg.Text(
                    text="Configure the colors for the game",
                    expand_x=True,
                    justification="center",
                )
            ],
            [
                sg.Text(
                    text="Orange color selection",
                    expand_x=True,
                    justification="center",
                    key="-Info_Color_Selection-",
                )
            ],
            [
                sg.Graph(
                    canvas_size=(640, 480),
                    graph_bottom_left=(0, 0),
                    graph_top_right=(640, 480),
                    enable_events=True,
                    background_color="white",
                    key="-Graph-",
                ),
                sg.Column(
                    layout=[
                        [
                            sg.Radio(
                                "Orange color",
                                key="-Step_Orange-",
                                group_id=1,
                                default=True,
                            )
                        ],
                        [
                            sg.Radio(
                                text="Blue color",
                                key="-Step_Blue-",
                                group_id=1,
                                enable_events=True,
                            )
                        ],
                        [
                            sg.Radio(
                                text="Black color",
                                key="-Step_Black-",
                                group_id=1,
                                enable_events=True,
                            )
                        ],
                        [
                            sg.Radio(
                                text="White color",
                                key="-Step_White-",
                                group_id=1,
                                enable_events=True,
                            )
                        ],
                    ]
                ),
            ],
            [sg.Button("Next", key="-End_Configuration-")],
        ]
        return layout

    def _show_port_selection_tab(self) -> None:
        self._window["-Port_Selection-"].update(visible=True)

    def _show_color_configuration_tab(self) -> None:
        self._window["-Color_Configuration-"].update(visible=True)

    def _update_selected_color_label(self) -> None:
        self._window["-Selected_Color-"].update(
            f"Selected Color for robot is: {self._selected_color}"
        )

    def run(self) -> None:
        while True:
            event, values = self._window.read(20)
            if event in [sg.WIN_CLOSED, "Cancel"]:
                break
            elif event == "-Select_Orange-":
                self._selected_color = "Orange"
                self._update_selected_color_label()
                self._show_port_selection_tab()
            elif event == "-Select_Blue-":
                self._selected_color = "Blue"
                self._update_selected_color_label()
                self._show_port_selection_tab()

            elif (
                event == "-TABGROUP-"
                and values["-TABGROUP-"] != "-Color_Configuration-"
                and self._recording
            ):
                self._recording = False
                if self._cap:
                    self._cap.release()
                    self._cap = None

            elif event == "-Camera_Port-":
                self._camera_port = int(values["-Camera_Port-"])

            elif event == "-Robot_Port-":
                self._robot_port = values["-Robot_Port-"]

            elif not self._window["-Color_Configuration-"].visible and None not in [
                self._camera_port,
                self._robot_port,
            ]:
                self._show_color_configuration_tab()

            elif (
                event == "-TABGROUP-"
                and values["-TABGROUP-"] == "-Color_Configuration-"
                and not self._recording
            ):
                if self._camera_port is not None:
                    self._cap = cv2.VideoCapture(self._camera_port)
                    if not self._cap.isOpened():
                        sg.popup("Failed to access the camera.")
                    else:
                        self._recording = True
                else:
                    sg.popup("No camera port selected!")

            if self._cap is not None and self._cap.isOpened() and self._recording:
                ret, frame = self._cap.read()
                if ret:
                    self._frame = frame
                    imgbytes = cv2.imencode(".png", frame)[1].tobytes()
                    if self._image_id:
                        self._window["-Graph-"].delete_figure(self._image_id)
                    self._image_id = self._window["-Graph-"].draw_image(
                        data=imgbytes, location=(0, 480)
                    )

            if values["-Step_Orange-"]:
                self._window["-Info_Color_Selection-"].update("Orange color selection")
            elif values["-Step_Blue-"]:
                self._window["-Info_Color_Selection-"].update("Blue color selection")
            elif values["-Step_Black-"]:
                self._window["-Info_Color_Selection-"].update("Black color selection")
            elif values["-Step_White-"]:
                self._window["-Info_Color_Selection-"].update("White color selection")

            if event == "-Graph-" and self._recording:
                mouse = values["-Graph-"]
                mouse_x, mouse_y = mouse
                mouse_y = 480 - mouse_y
                if self._frame is None:
                    continue

                if (
                    0 <= mouse_x < self._frame.shape[1]
                    and 0 <= mouse_y < self._frame.shape[0]
                ):
                    b, g, r = self._frame[mouse_y, mouse_x]
                    if values["-Step_Orange-"]:
                        self._selected_config_color = "Orange"
                    elif values["-Step_Blue-"]:
                        self._selected_config_color = "Blue"
                    elif values["-Step_Black-"]:
                        self._selected_config_color = "Black"
                    elif values["-Step_White-"]:
                        self._selected_config_color = "White"
                    if self._selected_config_color:
                        self._configuration_colors[self._selected_config_color] = (
                            r,
                            g,
                            b,
                        )
                        sg.popup(
                            f"Selected color for {self._selected_config_color} is: ({r}, {g}, {b})"
                        )

            if event == "-End_Configuration-":
                self._configuration_colors = {
                    key: tuple(map(int, self._configuration_colors[key]))
                    for key in self._configuration_colors
                }

                sg.popup(
                    "Selected colors for the game [R, G, B]",
                    f"Orange: {self._configuration_colors["Orange"]}\nBlue: {self._configuration_colors["Blue"]}\nBlack: {self._configuration_colors["Black"]}\nWhite: {self._configuration_colors["White"]}",
                )

                print(self._configuration_colors)

                break

        if self._cap:
            self._cap.release()
        self._window.close()


if __name__ == "__main__":
    app = ConfigurationWindow()
    app.run()
