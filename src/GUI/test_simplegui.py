import PySimpleGUI as sg
from serial.tools import list_ports
import cv2
from src.computer_vision.gameplay_recognition import (
    list_camera_ports as list_camera_ports,
)

# TODO: Delete this file before submition

class CheckersGUI:
    """Main application window for the Checkers Robot GUI using PySimpleGUI."""

    def __init__(self):
        self.selected_robot_port = None
        self.selected_camera_port = None
        self.rgb_values = {}
        self.current_step = 0
        self.steps = ["Select Orange", "Select Blue", "Select Dark", "Select White"]

        self.layout = [
            [
                sg.Text(
                    "Checkers Robot Configuration",
                    font=("Helvetica", 16),
                    justification="center",
                    expand_x=True,
                )
            ],
            [
                sg.TabGroup(
                    [
                        [
                            sg.Tab("Color Selection", self.color_selection_layout()),
                            sg.Tab("Port Selection", self.port_selection_layout()),
                            sg.Tab(
                                "Configure CV Colors", self.configure_cv_colors_layout()
                            ),
                        ]
                    ]
                )
            ],
            [sg.Button("Next", key="Next"), sg.Button("Exit")],
        ]

        self.window = sg.Window("Checkers Robot", self.layout, finalize=True)
        self.current_tab = "Color Selection"

    def color_selection_layout(self):
        layout = [
            [sg.Text("Select a robot color", size=(30, 1), justification="center")],
            [
                sg.Button(
                    image_filename="assets/checkers_img/orange.png", key="Select_Orange"
                ),
                sg.Button(
                    image_filename="assets/checkers_img/blue.png",
                    key="Select_Blue",
                    pad=(10, 0),
                ),
            ],
            [
                sg.Text(
                    "Selected Color for robot: None",
                    key="Selected_Color",
                    size=(30, 1),
                    justification="center",
                )
            ],
        ]
        return layout

    def port_selection_layout(self):
        robot_ports = [port.device for port in list_ports.comports()]
        _, camera_ports_list = list_camera_ports()
        camera_ports = [str(port) for port in camera_ports_list]

        layout = [
            [sg.Text("Select Robot's port")],
            [sg.Combo(robot_ports, key="Robot_Port")],
            [sg.Text("Select Camera's port")],
            [sg.Combo(camera_ports, key="Camera_Port")],
            [sg.Text("", key="Port_Selection_Message", size=(40, 1))],
        ]
        return layout

    def configure_cv_colors_layout(self):
        layout = [
            [sg.Image(key="Video_Frame")],
            [
                sg.Text(
                    f"Current step: {self.steps[self.current_step]}", key="Current_Step"
                )
            ],
            [sg.Button("Next Step", key="Next_Step")],
        ]
        return layout

    def run(self):
        while True:
            event, values = self.window.read(timeout=20)
            if event in (sg.WINDOW_CLOSED, "Exit"):
                break

            if event == "Select_Orange":
                self.selected_color = "Orange"
                self.window["Selected_Color"].update(
                    f"Selected Color for robot: {self.selected_color}"
                )
            elif event == "Select_Blue":
                self.selected_color = "Blue"
                self.window["Selected_Color"].update(
                    f"Selected Color for robot: {self.selected_color}"
                )

            if event == "Next":
                if self.current_tab == "Color Selection":
                    if not hasattr(self, "selected_color"):
                        sg.popup_error("You must select a color before moving forward.")
                    else:
                        self.window["Color Selection"].update(selected=True)
                        self.current_tab = "Port Selection"
                elif self.current_tab == "Port Selection":
                    robot_port = values.get("Robot_Port")
                    camera_port = values.get("Camera_Port")
                    if not robot_port or not camera_port:
                        sg.popup_error("Please select both robot and camera ports.")
                    else:
                        self.selected_robot_port = robot_port
                        self.selected_camera_port = int(camera_port)
                        self.window["Port Selection"].update(selected=True)
                        self.current_tab = "Configure CV Colors"
                elif self.current_tab == "Configure CV Colors":
                    sg.popup("Configuration Complete!")
                    print("Collected RGB values:", self.rgb_values)

            if self.current_tab == "Configure CV Colors":
                pass

            if event == "Next_Step":
                if self.current_step < len(self.steps) - 1:
                    self.current_step += 1
                    self.window["Current_Step"].update(
                        f"Current step: {self.steps[self.current_step]}"
                    )
                else:
                    sg.popup("All steps completed!")
                    print("Collected RGB values:", self.rgb_values)

        self.window.close()


if __name__ == "__main__":
    app = CheckersGUI()
    app.run()
