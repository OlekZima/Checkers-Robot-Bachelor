from pathlib import Path
import re
from typing import Optional

import cv2
import FreeSimpleGUI as sg
from serial.tools import list_ports

from src.common.configs import ColorConfig
from src.common.enums import Color, CalibrationMethod
from src.common.utils import CONFIG_PATH, detect_available_camera_ports

from src.robot_manipulation.calibration_controller import CalibrationController
from src.robot_manipulation.calibration_file_handler import CalibrationFileHandler


class ConfigurationWindow:
    """Configuration window for the checkers robot."""

    def __init__(self) -> None:
        self._selected_color: Optional[Color] = None
        self._difficulty_level: int = 3

        self._robot_port: Optional[str] = None
        self._camera_port: Optional[int] = None
        self._configuration_filename: Optional[str] = None

        self._cap: Optional[cv2.VideoCapture] = None
        self._frame = None
        self._image_id = None

        self._selected_config_color: Optional[str] = None

        self._config_method: Optional[CalibrationMethod] = None

        self._color_config: ColorConfig = ColorConfig(
            orange=(0, 0, 0),
            blue=(0, 0, 0),
            black=(0, 0, 0),
            white=(0, 0, 0),
        )

        self._controller: Optional[CalibrationController] = None

        self._window = sg.Window(
            "Configuration",
            self._setup_main_layout(),
            resizable=False,
            return_keyboard_events=True,
            use_default_focus=False,
        )

    def _get_property_if_exist(self, property_name: str):
        if getattr(self, property_name) is None:
            raise AttributeError(
                f"No {property_name} property!\nLooks like you didn't run the `run` method."
            )
        return getattr(self, property_name)

    def get_robot_port(self) -> str:
        """Returns the selected port for the robot."""
        return self._get_property_if_exist("_robot_port")

    def get_camera_port(self) -> int:
        """Returns the selected port for the camera."""
        return self._get_property_if_exist("_camera_port")

    def get_config_colors_dict(self) -> ColorConfig:
        """
        Returns the selected colors dictionary for the game.

        ```python
        {
            "orange": (r, g, b),
            "blue": (r, g, b),
            "black": (r, g, b),
            "white": (r, g, b),
        }
        ```
        """
        return self._get_property_if_exist("_color_config")

    def get_robot_color(self) -> Color:
        """Returns the selected color as enum (Color.ORANGE or Color.BLUE) for the robot."""
        return self._get_property_if_exist("_selected_color")

    def get_configuration_file_path(self) -> str:
        """Returns the selected configuration filename (without extension)."""
        return self._get_property_if_exist("_configuration_filename")

    def get_difficulty_level(self) -> int:
        """Returns selected difficulty level (original range is [1 ... 10])"""
        return self._get_property_if_exist("_difficulty_level")

    @staticmethod
    def _setup_main_layout() -> list[sg.Element]:
        layout: list[sg.Element] = [
            [
                sg.Text(
                    "Checkers Robot Configuration",
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
                                layout=ConfigurationWindow._setup_color_selection_layout(),
                                key="-Color_Selection-",
                            ),
                            sg.Tab(
                                "Port Selection",
                                layout=ConfigurationWindow._setup_port_selection_layout(),
                                key="-Port_Selection-",
                                visible=False,
                            ),
                            sg.Tab(
                                "Color Configuration",
                                layout=ConfigurationWindow._setup_color_configuration_layout(),
                                key="-Color_Configuration-",
                                visible=False,
                            ),
                            sg.Tab(
                                title="Calibration",
                                layout=ConfigurationWindow._setup_calibration_layout(),
                                key="-Calibration-",
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
    def _setup_color_selection_layout() -> list[sg.Element]:
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
            [
                sg.Text(
                    "Select difficulty level",
                    justification="center",
                    expand_x=True,
                ),
            ],
            [
                sg.Push(),
                sg.Slider(
                    (1, 10),
                    3,
                    orientation="horizontal",
                    enable_events=True,
                    key="-Difficulty_Level-",
                ),
                sg.Push(),
            ],
            [sg.VPush()],
        ]

        return layout

    @staticmethod
    def _setup_port_selection_layout() -> list[sg.Element]:
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
                ),
                sg.OptionMenu(
                    values=detect_available_camera_ports(15),
                    key="-Camera_Port-",
                    expand_x=True,
                ),
            ],
            [sg.VPush()],
        ]
        return layout

    @staticmethod
    def _setup_color_configuration_layout() -> list[sg.Element]:
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
            [sg.Button("Next", key="-End_Color_Configuration-")],
        ]
        return layout

    @staticmethod
    def _setup_calibration_layout() -> list[list[sg.Element]]:
        layout = [
            [
                sg.Text("Select calibration method"),
                sg.Radio(
                    text="Corner tiles",
                    group_id=2,
                    key="-Corner_Tiles_Method-",
                    enable_events=True,
                ),
                sg.Radio(
                    text="All tiles",
                    group_id=2,
                    key="-All_Tiles_Method-",
                    enable_events=True,
                ),
            ],
            [
                sg.VPush(),
                sg.Column(
                    [
                        [
                            sg.Button(
                                "Forward",
                                size=(8, 2),
                                pad=((60, 0), (5, 5)),
                                key="-Robot_Move_Forward-",
                            ),
                        ],
                        [
                            sg.Button(
                                "Left",
                                size=(8, 2),
                                pad=((10, 10), (5, 5)),
                                key="-Robot_Move_Left-",
                            ),
                            sg.Button("Right", size=(8, 2), key="-Robot_Move_Right-"),
                        ],
                        [
                            sg.Button(
                                "Backward",
                                size=(8, 2),
                                pad=((60, 0), (5, 5)),
                                key="-Robot_Move_Backward-",
                            ),
                        ],
                    ],
                    justification="center",
                    key="-Robot_XY_Movement_Controller-",
                    visible=False,
                ),
                sg.Column(
                    [
                        [
                            sg.Button(
                                "Up",
                                size=(8, 2),
                                pad=((60, 0), (5, 5)),
                                key="-Robot_Move_Up-",
                            ),
                        ],
                        [
                            sg.Button(
                                "Down",
                                size=(8, 2),
                                pad=((60, 0), (5, 5)),
                                key="-Robot_Move_Down-",
                            ),
                        ],
                    ],
                    justification="center",
                    key="-Robot_Z_Movement_Controller-",
                    visible=False,
                ),
                sg.VPush(),
            ],
            [
                sg.Push(),
                sg.Text(
                    "",
                    expand_x=True,
                    justification="center",
                    key="-Robot_Next_Position-",
                    visible=False,
                ),
                sg.Text(
                    "Current robot position: ",
                    expand_x=True,
                    justification="center",
                    key="-Robot_Position-",
                    visible=False,
                ),
                sg.Push(),
            ],
            [
                sg.VPush(),
            ],
            [
                sg.Button(
                    "Load config file and finish",
                    visible=True,
                    key="-Load_Config-",
                ),
                sg.Button(
                    "Next Calibration Step",
                    visible=False,
                    key="-Next_Calibration_Step-",
                ),
                sg.Button(
                    "Save Calibration Config",
                    visible=False,
                    key="-Save_Calibration_Config-",
                ),
            ],
        ]

        return layout

    def _show_port_selection_tab(self) -> None:
        port_selection_tab: sg.Tab = self._window["-Port_Selection-"]
        port_selection_tab.update(visible=True)

    def _show_color_configuration_tab(self) -> None:
        color_configuration_tab: sg.Tab = self._window["-Color_Configuration-"]
        color_configuration_tab.update(visible=True)

    def _show_calibration_tab(self) -> None:
        calibration_tab: sg.Tab = self._window["-Calibration-"]
        calibration_tab.update(visible=True)
        self._controller = CalibrationController(self.get_robot_port())

    def _show_calibration_controller(self) -> None:
        self._window["-Robot_XY_Movement_Controller-"].update(visible=True)
        self._window["-Robot_Z_Movement_Controller-"].update(visible=True)
        self._window["-Robot_Position-"].update(visible=True)
        self._window["-Robot_Next_Position-"].update(visible=True)
        self._window["-Next_Calibration_Step-"].update(visible=False)
        self._window["-Load_Config-"].update(visible=True)

    def _update_selected_color_label(self) -> None:
        text_label: sg.Text = self._window["-Selected_Color-"]
        text_label.update(f"Selected Color for robot is: {self._selected_color}")

    def _handle_graph_mouse_click_event(self, values) -> None:
        mouse = values["-Graph-"]
        mouse_x, mouse_y = mouse
        mouse_y = 480 - mouse_y
        if self._frame is None:
            return

        frame_y, frame_x, _ = self._frame.shape

        if 0 <= mouse_x <= frame_x and 0 <= mouse_y <= frame_y:
            b, g, r = self._frame[mouse_y, mouse_x]
            if values["-Step_Orange-"]:
                self._selected_config_color = "orange"
            elif values["-Step_Blue-"]:
                self._selected_config_color = "blue"
            elif values["-Step_Black-"]:
                self._selected_config_color = "black"
            elif values["-Step_White-"]:
                self._selected_config_color = "white"

            if self._selected_config_color is not None:
                color_tuple = (int(r), int(g), int(b))
                if self._selected_config_color == "orange":
                    self._color_config["orange"] = color_tuple
                elif self._selected_config_color == "blue":
                    self._color_config["blue"] = color_tuple
                elif self._selected_config_color == "black":
                    self._color_config["black"] = color_tuple
                elif self._selected_config_color == "white":
                    self._color_config["white"] = color_tuple
                sg.popup(
                    f"Selected color for {self._selected_config_color} is: {color_tuple}"
                )

    def _handle_load_config_event(self) -> None:
        config_path_str = sg.popup_get_file(
            message="Select a configuration file.",
            initial_folder=str(CONFIG_PATH),
            file_types=(("Configuration file", "*.txt"),),
            keep_on_top=True,
            no_window=True,
        )

        if config_path_str is None or config_path_str == "":
            return

        config_path = Path(config_path_str)
        self._configuration_filename = config_path.stem

        with open(config_path, "r", encoding="UTF-8") as f:
            lines = f.readlines()
            if len(lines) != 42:
                sg.popup(
                    f"Invalid configuration file named {config_path.name}"
                )
            else:
                sg.popup(
                    f"Configuration file {config_path.name} loaded successfully!"
                )

    def _handle_end_color_configuration_event(self) -> None:
        o = self._color_config["orange"]
        b = self._color_config["blue"]
        bk = self._color_config["black"]
        w = self._color_config["white"]
        self._color_config = ColorConfig(
            orange=(int(o[0]), int(o[1]), int(o[2])),
            blue=(int(b[0]), int(b[1]), int(b[2])),
            black=(int(bk[0]), int(bk[1]), int(bk[2])),
            white=(int(w[0]), int(w[1]), int(w[2])),
        )

        sg.popup(
            "Selected colors for the game [R, G, B]",
            f"""orange: {self._color_config["orange"]}
            blue: {self._color_config["blue"]}
            black: {self._color_config["black"]}
            white: {self._color_config["white"]}""",
        )

        self._show_calibration_tab()

    def _handle_next_frame_event(self) -> None:
        if self._cap is None:
            return
        ret, frame = self._cap.read()
        if ret:
            self._frame = frame
            imgbytes = cv2.imencode(".png", frame)[1].tobytes()
            if self._image_id:
                self._window["-Graph-"].delete_figure(self._image_id)
            self._image_id = self._window["-Graph-"].draw_image(
                data=imgbytes, location=(0, 480)
            )

    def _handle_robot_movement_event(self, event) -> None:
        if self._controller is None:
            return
        if event in ("-Robot_Move_Forward-", "w:25"):
            self._controller.move_forward()
        elif event in ("-Robot_Move_Backward-", "s:39"):
            self._controller.move_backward()
        elif event in ("-Robot_Move_Left-", "a:38"):
            self._controller.move_left()
        elif event in ("-Robot_Move_Right-", "d:40"):
            self._controller.move_right()
        elif event in ("-Robot_Move_Up-", "e:26"):
            self._controller.move_up()
        elif event in ("-Robot_Move_Down-", "q:24"):
            self._controller.move_down()

    def _start_all_tiles_calibration(self):
        """Start the all tiles calibration process."""
        self._handle_load_config_event()

        if self._configuration_filename is None:
            sg.popup_error("No configuration file selected. Calibration aborted.")
            return

        try:
            assert self._controller is not None
            config_path = CONFIG_PATH / f"{self._configuration_filename}.txt"
            self._controller.start_tile_calibration(config_path)

            self._update_calibration_instruction(CalibrationMethod.ALL)
            self._controller.move_to_current_position()

            self._window["-Next_Calibration_Step-"].update(visible=True)

        except Exception as e:
            sg.popup_error(f"Error preparing all tiles calibration: {str(e)}")

    def _start_corner_calibration(self):
        """Start the calibration process when entering the Calibration tab."""
        assert self._controller is not None
        self._controller.start_corner_calibration()
        self._update_calibration_instruction()
        self._controller.move_to_current_corner_position()

        # Show the Next Calibration Step button
        self._window["-Next_Calibration_Step-"].update(visible=True)

    def _update_calibration_instruction(
        self, calibration_method: Optional[CalibrationMethod] = CalibrationMethod.CORNER
    ):
        """Update the instruction displayed in the '-Robot_Next_Position-' Text element."""
        assert self._controller is not None
        if calibration_method == CalibrationMethod.ALL:
            instruction = self._controller.get_current_tile_step_description()
        else:
            instruction = self._controller.get_current_corner_step_description()
        if instruction:
            self._window["-Robot_Next_Position-"].update(instruction)

            self._window["-Next_Calibration_Step-"].update(disabled=False)
        else:
            self._window["-Robot_Next_Position-"].update("Calibration complete.")

            self._window["-Next_Calibration_Step-"].update(disabled=True)

    def _handle_calibration_step_completion(self):
        """Handle the completion of the current calibration step."""
        assert self._controller is not None
        if self._config_method == CalibrationMethod.CORNER:
            self._controller.save_current_corner_position()
            if not self._controller.is_corner_calibration_complete():
                self._update_calibration_instruction()
                self._controller.move_to_current_corner_position()
            else:
                self._window["-Robot_Next_Position-"].update("Calibration complete.")
                self._window["-Next_Calibration_Step-"].update(visible=False)
                self._window["-Save_Calibration_Config-"].update(visible=True)
                self._controller.finalize_corner_calibration()
                sg.popup(
                    "Calibration completed successfully!\nSave the configuration file",
                    keep_on_top=True,
                )
        else:
            self._controller.save_current_tile_position()
            if not self._controller.is_tile_calibration_complete():
                self._update_calibration_instruction(CalibrationMethod.ALL)
                self._controller.move_to_current_position()
            else:
                self._window["-Robot_Next_Position-"].update("Calibration complete.")
                self._window["-Next_Calibration_Step-"].update(visible=False)
                sg.popup(
                    "Calibration completed successfully!\nSave the configuration file",
                    keep_on_top=True,
                )
                filename = sg.popup_get_text(
                    "Enter configuration filename (without extension):",
                    title="Save Calibration Configuration",
                    default_text="calibration_config",
                    keep_on_top=True,
                )
                if filename is None:
                    sg.popup_error("No filename provided. Configuration not saved.")
                    return

                filename = re.sub(r"[^\w\-_\.]", "", filename)
                if not filename:
                    sg.popup_error("Invalid filename. Configuration not saved.")
                    return

                self._controller.save_tile_calibration(filename)

                config_path = CONFIG_PATH / f"{filename}.txt"
                sg.popup(
                    f"Calibration configuration saved to {config_path}",
                    title="Configuration Saved",
                    keep_on_top=True,
                )

                self._configuration_filename = filename
                sg.popup(
                    "End of calibration. Starting the game.",
                    title="Configuration complete",
                    keep_on_top=True,
                )

    def _save_calibration_config(self) -> None:
        """
        Save the calibration configuration to a file.
        Uses CalibrationFileHandler for corner calibration data.
        """
        try:
            filename = sg.popup_get_text(
                "Enter configuration filename (without extension):",
                title="Save Calibration Configuration",
                default_text="calibration_config",
                keep_on_top=True,
            )

            if filename is None:
                sg.popup_error("No filename provided. Configuration not saved.")
                return

            filename = re.sub(r"[^\w\-_\.]", "", filename)
            if not filename:
                sg.popup_error("Invalid filename. Configuration not saved.")
                return

            assert self._controller is not None
            calibration_data = self._controller.calibration_data
            if calibration_data is None:
                sg.popup_error("No calibration data available. Complete calibration first.")
                return

            handler = CalibrationFileHandler(CONFIG_PATH)
            handler.save_calibration(calibration_data, filename)

            config_path = CONFIG_PATH / f"{filename}.txt"
            sg.popup(
                f"Calibration configuration saved to {config_path}",
                title="Configuration Saved",
                keep_on_top=True,
            )

            self._configuration_filename = filename
            sg.popup(
                "End of calibration. Starting the game.",
                title="Configuration complete",
                keep_on_top=True,
            )

        except Exception as e:
            sg.popup_error(f"Error saving configuration: {str(e)}")

    def run(self) -> None:
        """Main loop for the configuration window."""
        recording = False
        while True:
            event, values = self._window.read(20)
            if event in [sg.WIN_CLOSED, "Cancel"]:
                break
            if event == "-Select_Orange-":
                self._selected_color = Color.ORANGE
                self._update_selected_color_label()
                self._show_port_selection_tab()
            if event == "-Select_Blue-":
                self._selected_color = Color.BLUE
                self._update_selected_color_label()
                self._show_port_selection_tab()

            if event == "-Difficulty_Level-":
                self._difficulty_level = int(values["-Difficulty_Level-"])

            if (
                event == "-TABGROUP-"
                and values["-TABGROUP-"] != "-Color_Configuration-"
                and recording
            ):
                recording = False
                if self._cap:
                    self._cap.release()
                    self._cap = None

            if event == "-Camera_Port-":
                self._camera_port = int(values["-Camera_Port-"])

            if event == "-Robot_Port-":
                self._robot_port = values["-Robot_Port-"]
                self._robot_port = self._robot_port[: self._robot_port.index(" ")]

            if not self._window["-Color_Configuration-"].visible and None not in [
                self._camera_port,
                self._robot_port,
            ]:
                self._show_color_configuration_tab()

            if (
                event == "-TABGROUP-"
                and values["-TABGROUP-"] == "-Color_Configuration-"
                and not recording
            ):
                if self._camera_port is not None:
                    self._cap = cv2.VideoCapture(self._camera_port)
                    if not self._cap.isOpened():
                        sg.popup("Failed to access the camera.")
                    else:
                        recording = True
                else:
                    sg.popup("No camera port selected!")

            if event == "-All_Tiles_Method-":
                self._window["-Corner_Tiles_Method-"].update(disabled=True)
                self._window["-All_Tiles_Method-"].update(disabled=True)
                self._show_calibration_controller()
                self._config_method = CalibrationMethod.ALL
                self._start_all_tiles_calibration()

            if event == "-Corner_Tiles_Method-":
                self._window["-Corner_Tiles_Method-"].update(disabled=True)
                self._window["-All_Tiles_Method-"].update(disabled=True)
                self._show_calibration_controller()
                self._config_method = CalibrationMethod.CORNER
                self._start_corner_calibration()

            if self._controller is not None:
                if event in ("-Robot_Move_Forward-", "w:25"):
                    self._controller.move_forward()
                elif event in ("-Robot_Move_Backward-", "s:39"):
                    self._controller.move_backward()
                elif event in ("-Robot_Move_Left-", "a:38"):
                    self._controller.move_left()
                elif event in ("-Robot_Move_Right-", "d:40"):
                    self._controller.move_right()
                elif event in ("-Robot_Move_Up-", "e:26"):
                    self._controller.move_up()
                elif event in ("-Robot_Move_Down-", "q:24"):
                    self._controller.move_down()

            if self._cap is not None and self._cap.isOpened() and recording:
                self._handle_next_frame_event()

            if values["-Step_Orange-"]:
                self._window["-Info_Color_Selection-"].update("Orange color selection")
            elif values["-Step_Blue-"]:
                self._window["-Info_Color_Selection-"].update("Blue color selection")
            elif values["-Step_Black-"]:
                self._window["-Info_Color_Selection-"].update("Black color selection")
            elif values["-Step_White-"]:
                self._window["-Info_Color_Selection-"].update("White color selection")

            if event == "-Graph-" and recording:
                self._handle_graph_mouse_click_event(values)

            if event == "-End_Color_Configuration-":
                self._handle_end_color_configuration_event()

            if event == "-Load_Config-":
                self._handle_load_config_event()
                self._window.close()

            if event == "-Next_Calibration_Step-":
                self._handle_calibration_step_completion()

            if event == "-Save_Calibration_Config-":
                self._save_calibration_config()
                self._window.close()

        if self._cap:
            self._cap.release()
        self._window.close()
