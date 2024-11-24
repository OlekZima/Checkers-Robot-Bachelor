import re
import PySimpleGUI as sg
from serial.tools import list_ports
import cv2
from src.computer_vision.gameplay_recognition import list_camera_ports


class ColorSelection:
    def __init__(self) -> None:
        self.selected_color = "Orange"

        self.recording = False
        self.robot_port = None
        self.camera_port = None
        self.cap = None
        self.frame = None
        self.image_id = None

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
                            ),
                            sg.Tab(
                                "Port Selection",
                                layout=ColorSelection._setup_port_selection(),
                            ),
                            sg.Tab(
                                "Color Configuration",
                                layout=ColorSelection._setup_color_configuration(),
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
            [
                sg.Text("Select port for the robot:", expand_x=True),
                sg.Text(
                    "Select port for the camera:", expand_x=True, justification="right"
                ),
            ],
            [
                sg.VPush(),
                sg.OptionMenu(
                    values=list_ports.comports(),
                    key="-Robot_Port-",
                    default_value="/dev/ttyUSB0",
                    expand_x=True,
                    enable_events=True,
                ),
                sg.OptionMenu(
                    values=list_camera_ports(),
                    key="-Camera_Port-",
                    default_value="0",
                    expand_x=True,
                    enable_events=True,
                ),
                sg.VPush(),
            ],
        ]
        return layout

    @staticmethod
    def _setup_color_configuration() -> list[sg.Element]:
        layout = [
            [
                sg.Text(
                    "Configure the colors for the game",
                    expand_x=True,
                    justification="center",
                )
            ],
            [sg.Text("Orange color selection", expand_x=True, justification="center")],
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
                    [
                        [sg.Radio("Orange color", key="-Step_Orange-", group_id=1, default=True)],
                        [sg.Radio("Blue color", key="-Step_Blue-", group_id=1)],
                        [sg.Radio("Black color", key="-Step_Black-", group_id=1)],
                        [sg.Radio("White color", key="-Step_White-", group_id=1)],
                    ]
                ),
            ],
            [sg.Button("Next", key="-End_Configuration-")],
        ]
        return layout

    def run(self) -> None:
        while True:
            event, values = self.window.read(20)
            if event in [sg.WIN_CLOSED, "Cancel"]:
                break
            elif event == "-Select_Orange-":
                self.selected_color = "Orange"
                self.window["-Selected_Color-"].update(
                    f"Selected Color for robot is: {self.selected_color}"
                )
            elif event == "-Select_Blue-":
                self.selected_color = "Blue"
                self.window["-Selected_Color-"].update(
                    f"Selected Color for robot is: {self.selected_color}"
                )

            elif (
                event == "-TABGROUP-"
                and values["-TABGROUP-"] != "Color Configuration"
                and self.recording
            ):
                self.recording = False
                if self.cap:
                    self.cap.release()
                    self.cap = None

            elif (
                event == "-TABGROUP-"
                and values["-TABGROUP-"] == "Color Configuration"
                and not self.recording
            ):
                camera_port_selection = values["-Camera_Port-"]
                if camera_port_selection and camera_port_selection != "/dev/ttyUSB0":
                    self.camera_port = int(
                        re.search("[0-9]+", camera_port_selection).group()
                    )
                    self.cap = cv2.VideoCapture(self.camera_port)
                    if not self.cap.isOpened():
                        sg.popup("Failed to access the camera.")
                    else:
                        self.recording = True

            if self.cap is not None and self.cap.isOpened() and self.recording:
                ret, frame = self.cap.read()
                if ret:
                    self.frame = frame
                    imgbytes = cv2.imencode(".png", frame)[1].tobytes()
                    if self.image_id:
                        self.window["-Graph-"].delete_figure(self.image_id)
                    self.image_id = self.window["-Graph-"].draw_image(data=imgbytes, location=(0, 480))

            if event == "-Graph-" and self.recording:
                mouse = values["-Graph-"]
                mouse_x, mouse_y = mouse
                mouse_y = 480 - mouse_y
                if self.frame is not None:
                    if 0 <= mouse_x < self.frame.shape[1] and 0 <= mouse_y < self.frame.shape[0]:
                        b, g, r = self.frame[mouse_y, mouse_x]
                        selected_color = None
                        if values["-Step_Orange-"]:
                            selected_color = "Orange"
                        elif values["-Step_Blue-"]:
                            selected_color = "Blue"
                        elif values["-Step_Black-"]:
                            selected_color = "Black"
                        elif values["-Step_White-"]:
                            selected_color = "White"
                        if selected_color:
                            self.configuration_colors[selected_color] = (r, g, b)
                            sg.popup(f"Color for {selected_color} updated to: {r}, {g}, {b}")
                        else:
                            sg.popup("Select a color to update")

            if event == "-End_Configuration-":
                sg.popup("Selected colors for the game", self.configuration_colors)
                break


        if self.cap:
            self.cap.release()
        self.window.close()


if __name__ == "__main__":
    app = ColorSelection()
    app.run()
