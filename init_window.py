import PySimpleGUI as sg
from serial.tools import list_ports
import cv2
from src.computer_vision.gameplay_recognition import list_camera_ports


class ColorSelection:
    def __init__(self) -> None:
        self.selected_color = None

        self.recording = False
        self.robot_port = None
        self.camera_port = None
        self.cap = None
        self.frame = None
        self.image_id = None

        self.selected_config_color = None

        self.configuration_colors: dict[str, tuple[int, int, int]] = {
            "Orange": (0, 0, 0),
            "Blue": (0, 0, 0),
            "Black": (0, 0, 0),
            "White": (0, 0, 0),
        }

        self.window = sg.Window(
            "Configuration", self._setup_main_layout(), resizable=False
        )

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
                                layout=ColorSelection._setup_color_selection(),
                                key="-Color_Selection-",
                            ),
                            sg.Tab(
                                "Port Selection",
                                layout=ColorSelection._setup_port_selection(),
                                key="-Port_Selection-",
                                visible=False,
                            ),
                            sg.Tab(
                                "Color Configuration",
                                layout=ColorSelection._setup_color_configuration(),
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
        self.window["-Port_Selection-"].update(visible=True)

    def _update_selected_color_label(self) -> None:
        self.window["-Selected_Color-"].update(
            f"Selected Color for robot is: {self.selected_color}"
        )

    def run(self) -> None:
        while True:
            event, values = self.window.read(20)
            if event in [sg.WIN_CLOSED, "Cancel"]:
                break
            elif event == "-Select_Orange-":
                self.selected_color = "Orange"
                self._update_selected_color_label()
                self._show_port_selection_tab()
            elif event == "-Select_Blue-":
                self.selected_color = "Blue"
                self._update_selected_color_label()
                self._show_port_selection_tab()

            elif (
                event == "-TABGROUP-"
                and values["-TABGROUP-"] != "-Color_Configuration-"
                and self.recording
            ):
                self.recording = False
                if self.cap:
                    self.cap.release()
                    self.cap = None

            elif event == "-Camera_Port-":
                self.camera_port = int(values["-Camera_Port-"])

            elif event == "-Robot_Port-":
                self.robot_port = values["-Robot_Port-"]

            elif not self.window["-Color_Configuration-"].visible and None not in [
                self.camera_port,
                self.robot_port,
            ]:
                self.window["-Color_Configuration-"].update(visible=True)

            elif (
                event == "-TABGROUP-"
                and values["-TABGROUP-"] == "-Color_Configuration-"
                and not self.recording
            ):
                if self.camera_port is not None:
                    self.cap = cv2.VideoCapture(self.camera_port)
                    if not self.cap.isOpened():
                        sg.popup("Failed to access the camera.")
                    else:
                        self.recording = True
                else:
                    sg.popup("No camera port selected!")

            if self.cap is not None and self.cap.isOpened() and self.recording:
                ret, frame = self.cap.read()
                if ret:
                    self.frame = frame
                    imgbytes = cv2.imencode(".png", frame)[1].tobytes()
                    if self.image_id:
                        self.window["-Graph-"].delete_figure(self.image_id)
                    self.image_id = self.window["-Graph-"].draw_image(
                        data=imgbytes, location=(0, 480)
                    )

            if values["-Step_Orange-"]:
                self.window["-Info_Color_Selection-"].update("Orange color selection")
            elif values["-Step_Blue-"]:
                self.window["-Info_Color_Selection-"].update("Blue color selection")
            elif values["-Step_Black-"]:
                self.window["-Info_Color_Selection-"].update("Black color selection")
            elif values["-Step_White-"]:
                self.window["-Info_Color_Selection-"].update("White color selection")

            if event == "-Graph-" and self.recording:
                mouse = values["-Graph-"]
                mouse_x, mouse_y = mouse
                mouse_y = 480 - mouse_y
                if self.frame is None:
                    continue

                if (
                    0 <= mouse_x < self.frame.shape[1]
                    and 0 <= mouse_y < self.frame.shape[0]
                ):
                    b, g, r = self.frame[mouse_y, mouse_x]
                    if values["-Step_Orange-"]:
                        self.selected_config_color = "Orange"
                    elif values["-Step_Blue-"]:
                        self.selected_config_color = "Blue"
                    elif values["-Step_Black-"]:
                        self.selected_config_color = "Black"
                    elif values["-Step_White-"]:
                        self.selected_config_color = "White"
                    if self.selected_config_color:
                        self.configuration_colors[self.selected_config_color] = (
                            r,
                            g,
                            b,
                        )
                        sg.popup(
                            f"Selected color for {self.selected_config_color} is: ({r}, {g}, {b})"
                        )

            if event == "-End_Configuration-":
                self.configuration_colors = {
                    key: tuple(map(int, self.configuration_colors[key]))
                    for key in self.configuration_colors
                }

                sg.popup(
                    "Selected colors for the game [R, G, B]",
                    f"Orange: {self.configuration_colors["Orange"]}\nBlue: {self.configuration_colors["Blue"]}\nBlack: {self.configuration_colors["Black"]}\nWhite: {self.configuration_colors["White"]}",
                )

                print(self.configuration_colors)

                break

        if self.cap:
            self.cap.release()
        self.window.close()


if __name__ == "__main__":
    app = ColorSelection()
    app.run()
