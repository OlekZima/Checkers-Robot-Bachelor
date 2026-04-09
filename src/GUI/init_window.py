from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional, cast

import cv2
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from serial.tools import list_ports

from src.common.configs import ColorConfig
from src.common.enums import CalibrationMethod, Color
from src.common.utils import CONFIG_PATH, detect_available_camera_ports
from src.robot_manipulation.calibration_controller import CalibrationController


class ConfigurationWindow:
    """Configuration window for the checkers robot."""

    def __init__(self) -> None:
        self._selected_color: Optional[Color] = None
        self._difficulty_level: int = 3

        self._robot_port: Optional[str] = None
        self._camera_port: Optional[int] = None
        self._configuration_file_path: Optional[Path] = None

        self._cap = None
        self._frame = None

        self._selected_config_color: Optional[str] = None
        self._config_method: Optional[CalibrationMethod] = None

        self._color_config: ColorConfig = cast(
            ColorConfig,
            {
                "orange": (0, 0, 0),
                "blue": (0, 0, 0),
                "black": (0, 0, 0),
                "white": (0, 0, 0),
            },
        )

        self._controller: Optional[CalibrationController] = None

        self._app = QApplication.instance() or QApplication([])
        self._window = QDialog()
        self._window.setWindowTitle("Configuration")
        self._window.setMinimumSize(980, 780)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_color_selection_tab(), "Color Selection")
        self._tabs.addTab(self._create_port_selection_tab(), "Port Selection")
        self._tabs.addTab(self._create_color_configuration_tab(), "Color Configuration")
        self._tabs.addTab(self._create_calibration_tab(), "Calibration")
        self._tabs.setTabEnabled(1, False)
        self._tabs.setTabEnabled(2, False)
        self._tabs.setTabEnabled(3, False)
        self._tabs.currentChanged.connect(self._on_tab_changed)

        layout = QVBoxLayout(self._window)
        layout.addWidget(self._tabs)

        self._camera_timer = QTimer(self._window)
        self._camera_timer.timeout.connect(self._update_camera_frame)

    def _create_color_selection_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("Select Robot's color")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 18px;")

        self._selected_color_label = QLabel("Selected Color for robot is: None")
        self._selected_color_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._orange_button = QPushButton()
        orange_pixmap = QPixmap("assets/checkers_img/orange.png")
        if not orange_pixmap.isNull():
            self._orange_button.setIcon(QIcon(orange_pixmap))
            self._orange_button.setIconSize(orange_pixmap.size())
            self._orange_button.setFixedSize(120, 120)
        else:
            self._orange_button.setText("Orange")
        self._orange_button.clicked.connect(lambda: self._set_robot_color(Color.ORANGE))

        self._blue_button = QPushButton()
        blue_pixmap = QPixmap("assets/checkers_img/blue.png")
        if not blue_pixmap.isNull():
            self._blue_button.setIcon(QIcon(blue_pixmap))
            self._blue_button.setIconSize(blue_pixmap.size())
            self._blue_button.setFixedSize(120, 120)
        else:
            self._blue_button.setText("Blue")
        self._blue_button.clicked.connect(lambda: self._set_robot_color(Color.BLUE))

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self._orange_button)
        button_layout.addWidget(self._blue_button)
        button_layout.addStretch()

        difficulty_label = QLabel("Select difficulty level")
        difficulty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._difficulty_spinbox = QSpinBox()
        self._difficulty_spinbox.setRange(1, 10)
        self._difficulty_spinbox.setValue(3)
        self._difficulty_spinbox.valueChanged.connect(self._on_difficulty_changed)
        self._difficulty_spinbox.setFixedWidth(100)

        difficulty_layout = QHBoxLayout()
        difficulty_layout.addStretch()
        difficulty_layout.addWidget(self._difficulty_spinbox)
        difficulty_layout.addStretch()

        layout.addStretch()
        layout.addWidget(title)
        layout.addLayout(button_layout)
        layout.addWidget(self._selected_color_label)
        layout.addStretch()
        layout.addWidget(difficulty_label)
        layout.addLayout(difficulty_layout)
        layout.addStretch()

        return tab

    def _create_port_selection_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("Select ports for robot and camera")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 16px;")

        self._robot_port_combo = QComboBox()
        self._camera_port_combo = QComboBox()

        for port in list_ports.comports():
            self._robot_port_combo.addItem(
                f"{port.device} ({port.description})", port.device
            )

        self._robot_port_combo.currentIndexChanged.connect(self._on_robot_port_changed)
        self._camera_port_combo.currentIndexChanged.connect(
            self._on_camera_port_changed
        )

        available_cameras = detect_available_camera_ports()
        for port in available_cameras:
            self._camera_port_combo.addItem(str(port), port)

        grid = QGridLayout()
        grid.addWidget(QLabel("Robot port:"), 0, 0)
        grid.addWidget(self._robot_port_combo, 0, 1)
        grid.addWidget(QLabel("Camera port:"), 1, 0)
        grid.addWidget(self._camera_port_combo, 1, 1)

        layout.addWidget(title)
        layout.addLayout(grid)
        layout.addStretch()

        return tab

    def _create_color_configuration_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        header = QLabel("Configure the colors for the game")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-weight: bold; font-size: 16px;")

        self._info_color_selection = QLabel("Orange color selection")
        self._info_color_selection.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._image_label = QLabel()
        self._image_label.setFixedSize(640, 480)
        self._image_label.setStyleSheet(
            "background-color: white; border: 1px solid black;"
        )
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.mousePressEvent = cast(Any, self._on_color_image_mouse_press)

        self._radio_orange = QRadioButton("Orange color")
        self._radio_blue = QRadioButton("Blue color")
        self._radio_black = QRadioButton("Black color")
        self._radio_white = QRadioButton("White color")
        self._radio_orange.setChecked(True)

        self._radio_orange.toggled.connect(
            lambda: self._info_color_selection.setText("Orange color selection")
        )
        self._radio_blue.toggled.connect(
            lambda: self._info_color_selection.setText("Blue color selection")
        )
        self._radio_black.toggled.connect(
            lambda: self._info_color_selection.setText("Black color selection")
        )
        self._radio_white.toggled.connect(
            lambda: self._info_color_selection.setText("White color selection")
        )

        radio_layout = QVBoxLayout()
        radio_layout.addWidget(self._radio_orange)
        radio_layout.addWidget(self._radio_blue)
        radio_layout.addWidget(self._radio_black)
        radio_layout.addWidget(self._radio_white)

        next_button = QPushButton("Next")
        next_button.clicked.connect(self._handle_end_color_configuration_event)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self._image_label)
        controls_layout.addLayout(radio_layout)

        layout.addWidget(header)
        layout.addWidget(self._info_color_selection)
        layout.addLayout(controls_layout)
        layout.addWidget(next_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        return tab

    def _create_calibration_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        method_layout = QHBoxLayout()
        self._corner_method_radio = QRadioButton("Corner tiles")
        self._all_tiles_method_radio = QRadioButton("All tiles")
        self._corner_method_radio.toggled.connect(self._on_method_selected)
        self._all_tiles_method_radio.toggled.connect(self._on_method_selected)

        method_layout.addWidget(QLabel("Select calibration method:"))
        method_layout.addWidget(self._corner_method_radio)
        method_layout.addWidget(self._all_tiles_method_radio)

        self._robot_xy_controls = QGroupBox("XY Movement")
        xy_layout = QGridLayout()
        self._robot_forward_button = QPushButton("Forward")
        self._robot_left_button = QPushButton("Left")
        self._robot_right_button = QPushButton("Right")
        self._robot_backward_button = QPushButton("Backward")
        self._robot_up_button = QPushButton("Up")
        self._robot_down_button = QPushButton("Down")

        self._robot_forward_button.clicked.connect(
            lambda: self._handle_robot_movement_event("forward")
        )
        self._robot_backward_button.clicked.connect(
            lambda: self._handle_robot_movement_event("backward")
        )
        self._robot_left_button.clicked.connect(
            lambda: self._handle_robot_movement_event("left")
        )
        self._robot_right_button.clicked.connect(
            lambda: self._handle_robot_movement_event("right")
        )
        self._robot_up_button.clicked.connect(
            lambda: self._handle_robot_movement_event("up")
        )
        self._robot_down_button.clicked.connect(
            lambda: self._handle_robot_movement_event("down")
        )

        xy_layout.addWidget(self._robot_forward_button, 0, 1)
        xy_layout.addWidget(self._robot_left_button, 1, 0)
        xy_layout.addWidget(self._robot_right_button, 1, 2)
        xy_layout.addWidget(self._robot_backward_button, 2, 1)
        self._robot_xy_controls.setLayout(xy_layout)
        self._robot_xy_controls.setVisible(False)

        self._robot_z_controls = QGroupBox("Z Movement")
        z_layout = QVBoxLayout()
        z_layout.addWidget(self._robot_up_button)
        z_layout.addWidget(self._robot_down_button)
        self._robot_z_controls.setLayout(z_layout)
        self._robot_z_controls.setVisible(False)

        self._robot_next_position_label = QLabel("")
        self._robot_next_position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._robot_next_position_label.setVisible(False)

        self._robot_position_label = QLabel("Current robot position:")
        self._robot_position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._robot_position_label.setVisible(False)

        button_row = QHBoxLayout()
        self._load_config_button = QPushButton("Load config file and finish")
        self._next_step_button = QPushButton("Next Calibration Step")
        self._save_config_button = QPushButton("Save Calibration Config")

        self._load_config_button.clicked.connect(self._handle_load_config_event)
        self._next_step_button.clicked.connect(self._handle_calibration_step_completion)
        self._save_config_button.clicked.connect(self._save_calibration_config)

        self._next_step_button.setVisible(False)
        self._save_config_button.setVisible(False)

        button_row.addWidget(self._load_config_button)
        button_row.addWidget(self._next_step_button)
        button_row.addWidget(self._save_config_button)

        layout.addLayout(method_layout)
        layout.addWidget(self._robot_xy_controls)
        layout.addWidget(self._robot_z_controls)
        layout.addWidget(self._robot_next_position_label)
        layout.addWidget(self._robot_position_label)
        layout.addLayout(button_row)
        layout.addStretch()

        return tab

    def _set_robot_color(self, color: Color) -> None:
        self._selected_color = color
        self._selected_color_label.setText(f"Selected Color for robot is: {color}")
        self._tabs.setTabEnabled(1, True)
        self._tabs.setCurrentIndex(1)

    def _on_difficulty_changed(self, value: int) -> None:
        self._difficulty_level = value

    def _on_robot_port_changed(self, index: int) -> None:
        port = self._robot_port_combo.itemData(index)
        if isinstance(port, str):
            self._robot_port = port
        self._try_enable_color_configuration_tab()

    def _on_camera_port_changed(self, index: int) -> None:
        port = self._camera_port_combo.itemData(index)
        if isinstance(port, int):
            self._camera_port = port
        self._try_enable_color_configuration_tab()

    def _try_enable_color_configuration_tab(self) -> None:
        if self._robot_port and self._camera_port is not None:
            self._tabs.setTabEnabled(2, True)

    def _on_tab_changed(self, index: int) -> None:
        if index == 2:
            if self._camera_port is None:
                self._show_message("No camera port selected!", QMessageBox.Icon.Warning)
                return
            self._start_camera_preview()
        else:
            self._stop_camera_preview()

    def _start_camera_preview(self) -> None:
        if self._camera_port is None:
            return
        if self._cap is not None:
            self._cap.release()
        self._cap = cv2.VideoCapture(self._camera_port)
        if not self._cap.isOpened():
            self._show_message(
                "Failed to access the camera.", QMessageBox.Icon.Critical
            )
            self._cap = None
            return
        self._camera_timer.start(33)

    def _stop_camera_preview(self) -> None:
        if self._camera_timer.isActive():
            self._camera_timer.stop()
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _update_camera_frame(self) -> None:
        if self._cap is None:
            return
        ret, frame = self._cap.read()
        if not ret or frame is None:
            return
        self._frame = frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = frame_rgb.shape
        bytes_per_line = width * channel
        q_image = QImage(
            frame_rgb.data.tobytes(),
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )
        pixmap = QPixmap.fromImage(q_image)
        self._image_label.setPixmap(
            pixmap.scaled(
                self._image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _handle_graph_mouse_click_event(self, x: int, y: int) -> None:
        if self._frame is None:
            return
        frame_height, frame_width, _ = self._frame.shape
        if x < 0 or y < 0 or x >= frame_width or y >= frame_height:
            return

        b, g, r = self._frame[y, x]
        self._selected_config_color = self._get_selected_color_name()
        if self._selected_config_color is None:
            return

        if self._selected_config_color == "orange":
            self._color_config["orange"] = (int(r), int(g), int(b))
        elif self._selected_config_color == "blue":
            self._color_config["blue"] = (int(r), int(g), int(b))
        elif self._selected_config_color == "black":
            self._color_config["black"] = (int(r), int(g), int(b))
        elif self._selected_config_color == "white":
            self._color_config["white"] = (int(r), int(g), int(b))
        self._show_message(
            f"Selected color for {self._selected_config_color} is: ({r}, {g}, {b})",
            QMessageBox.Icon.Information,
        )

    def _get_selected_color_name(self) -> Optional[str]:
        if self._radio_orange.isChecked():
            return "orange"
        if self._radio_blue.isChecked():
            return "blue"
        if self._radio_black.isChecked():
            return "black"
        if self._radio_white.isChecked():
            return "white"
        return None

    def _handle_load_config_event(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self._window,
            "Select a configuration file.",
            str(CONFIG_PATH),
            "Configuration file (*.txt)",
        )
        if not file_path:
            return

        selected_path = Path(file_path)
        try:
            with selected_path.open("r", encoding="UTF-8") as config_file:
                lines = config_file.readlines()
                if len(lines) != 42:
                    raise ValueError("Invalid configuration file length.")
        except Exception as exc:
            self._show_message(
                f"Invalid configuration file: {exc}", QMessageBox.Icon.Critical
            )
            return

        self._configuration_file_path = Path(selected_path.name)
        self._show_message(
            f"Configuration file {selected_path.name} loaded successfully!",
            QMessageBox.Icon.Information,
        )
        self._window.accept()

    def _handle_end_color_configuration_event(self) -> None:
        self._color_config = cast(
            ColorConfig,
            {
                "orange": tuple(map(int, self._color_config["orange"])),
                "blue": tuple(map(int, self._color_config["blue"])),
                "black": tuple(map(int, self._color_config["black"])),
                "white": tuple(map(int, self._color_config["white"])),
            },
        )
        message = (
            "Selected colors for the game [R, G, B]"
            + f"\nOrange: {self._color_config['orange']}"
            f"\nBlue: {self._color_config['blue']}"
            f"\nBlack: {self._color_config['black']}"
            f"\nWhite: {self._color_config['white']}"
        )
        self._show_message(message, QMessageBox.Icon.Information)
        self._tabs.setTabEnabled(3, True)
        self._tabs.setCurrentIndex(3)

    def _handle_robot_movement_event(self, direction: str) -> None:
        if self._controller is None:
            return
        if direction == "forward":
            self._controller.move_forward()
        elif direction == "backward":
            self._controller.move_backward()
        elif direction == "left":
            self._controller.move_left()
        elif direction == "right":
            self._controller.move_right()
        elif direction == "up":
            self._controller.move_up()
        elif direction == "down":
            self._controller.move_down()

    def _on_method_selected(self) -> None:
        if (
            self._corner_method_radio.isChecked()
            or self._all_tiles_method_radio.isChecked()
        ):
            self._corner_method_radio.setDisabled(True)
            self._all_tiles_method_radio.setDisabled(True)
            self._robot_xy_controls.setVisible(True)
            self._robot_z_controls.setVisible(True)
            self._robot_next_position_label.setVisible(True)
            self._robot_position_label.setVisible(True)
            self._load_config_button.setVisible(True)
            self._show_calibration_controller()

            if self._all_tiles_method_radio.isChecked():
                self._config_method = CalibrationMethod.ALL
                self._start_all_tiles_calibration()
            else:
                self._config_method = CalibrationMethod.CORNER
                self._start_corner_calibration()

    def _show_calibration_controller(self) -> None:
        if self._robot_port is None:
            self._show_message(
                "Select a robot port before calibration.", QMessageBox.Icon.Warning
            )
            return
        self._controller = CalibrationController(self._robot_port)

    def _on_color_image_mouse_press(self, event) -> None:
        if event is None or event.button() != Qt.MouseButton.LeftButton:
            return
        position = event.position()
        self._handle_graph_mouse_click_event(int(position.x()), int(position.y()))

    def _start_all_tiles_calibration(self) -> None:
        if self._configuration_file_path is None:
            self._show_message(
                "No configuration file selected. Calibration aborted.",
                QMessageBox.Icon.Critical,
            )
            return
        if self._controller is None:
            self._show_message(
                "Calibration controller is not initialized.", QMessageBox.Icon.Warning
            )
            return
        try:
            self._controller.start_tile_calibration(self._configuration_file_path)
            self._update_calibration_instruction(CalibrationMethod.ALL)
            self._controller.move_to_current_position()
            self._next_step_button.setVisible(True)
        except Exception as exc:
            self._show_message(
                f"Error preparing all tiles calibration: {exc}",
                QMessageBox.Icon.Critical,
            )

    def _handle_calibration_step_completion(self) -> None:
        if self._controller is None or self._config_method is None:
            return

        if self._config_method == CalibrationMethod.CORNER:
            self._controller.save_current_corner_position()
            if not self._controller.is_corner_calibration_complete():
                self._update_calibration_instruction()
                self._controller.move_to_current_corner_position()
            else:
                self._robot_next_position_label.setText("Calibration complete.")
                self._next_step_button.setVisible(False)
                self._save_config_button.setVisible(True)
                self._controller.finalize_corner_calibration()
                self._show_message(
                    "Calibration completed successfully! Save the configuration file.",
                    QMessageBox.Icon.Information,
                )
        else:
            self._controller.save_current_tile_position()
            if not self._controller.is_tile_calibration_complete():
                self._update_calibration_instruction(CalibrationMethod.ALL)
                self._controller.move_to_current_position()
            else:
                self._robot_next_position_label.setText("Calibration complete.")
                self._next_step_button.setVisible(False)
                self._show_message(
                    "Calibration completed successfully! Save the configuration file.",
                    QMessageBox.Icon.Information,
                )
                self._save_all_tiles_configuration()

    def _start_corner_calibration(self) -> None:
        if self._controller is None:
            self._show_message(
                "Calibration controller is not initialized.", QMessageBox.Icon.Warning
            )
            return
        self._controller.start_corner_calibration()
        self._update_calibration_instruction()
        self._controller.move_to_current_corner_position()
        self._next_step_button.setVisible(True)

    def _update_calibration_instruction(
        self,
        calibration_method: Optional[CalibrationMethod] = CalibrationMethod.CORNER,
    ) -> None:
        assert self._controller is not None
        if calibration_method == CalibrationMethod.ALL:
            instruction = self._controller.get_current_tile_step_description()
        else:
            instruction = self._controller.get_current_corner_step_description()
        if instruction:
            self._robot_next_position_label.setText(instruction)
            self._next_step_button.setEnabled(True)
        else:
            self._robot_next_position_label.setText("Calibration complete.")
            self._next_step_button.setEnabled(False)

    def _save_all_tiles_configuration(self) -> None:
        if self._controller is None:
            self._show_message(
                "Calibration controller is not initialized.", QMessageBox.Icon.Warning
            )
            return
        filename, _ = QFileDialog.getSaveFileName(
            self._window,
            "Save Calibration Configuration",
            str(CONFIG_PATH / "calibration_config.txt"),
            "Text Files (*.txt)",
        )
        if not filename:
            self._show_message(
                "No filename provided. Configuration not saved.",
                QMessageBox.Icon.Warning,
            )
            return
        safe_name = re.sub(r"[^\w\-_.]", "", Path(filename).stem)
        if not safe_name:
            self._show_message(
                "Invalid filename. Configuration not saved.", QMessageBox.Icon.Critical
            )
            return
        try:
            self._controller.save_tile_calibration(safe_name)
            self._configuration_file_path = Path(safe_name + ".txt")
            self._show_message(
                f"Calibration configuration saved to {CONFIG_PATH / (safe_name + '.txt')}",
                QMessageBox.Icon.Information,
            )
            self._show_message(
                "End of calibration. Starting the game.", QMessageBox.Icon.Information
            )
            self._window.accept()
        except Exception as exc:
            self._show_message(
                f"Error saving configuration: {exc}", QMessageBox.Icon.Critical
            )

    def _save_calibration_config(self) -> None:
        if self._controller is None:
            self._show_message(
                "No calibration controller initialized.", QMessageBox.Icon.Warning
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self._window,
            "Save Calibration Configuration",
            str(CONFIG_PATH / "calibration_config.txt"),
            "Text Files (*.txt)",
        )
        if not filename:
            self._show_message(
                "No filename provided. Configuration not saved.",
                QMessageBox.Icon.Warning,
            )
            return

        safe_name = re.sub(r"[^\w\-_.]", "", Path(filename).stem)
        if not safe_name:
            self._show_message(
                "Invalid filename. Configuration not saved.", QMessageBox.Icon.Critical
            )
            return

        try:
            self._controller.save_tile_calibration(safe_name)
            self._configuration_file_path = Path(safe_name + ".txt")
            self._show_message(
                f"Calibration configuration saved to {CONFIG_PATH / (safe_name + '.txt')}",
                QMessageBox.Icon.Information,
            )
            self._show_message(
                "End of calibration. Starting the game.", QMessageBox.Icon.Information
            )
            self._window.accept()
        except Exception as exc:
            self._show_message(
                f"Error saving configuration: {exc}", QMessageBox.Icon.Critical
            )

    def _show_message(
        self, message: str, icon: QMessageBox.Icon = QMessageBox.Icon.Information
    ) -> None:
        dialog = QMessageBox(self._window)
        dialog.setIcon(icon)
        dialog.setText(message)
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.exec()

    def _get_property_if_exist(self, property_name: str):
        if getattr(self, property_name) is None:
            raise AttributeError(
                f"No {property_name} property!\nLooks like you didn't run the `run` method."
            )
        return getattr(self, property_name)

    def get_robot_port(self) -> str:
        return self._get_property_if_exist("_robot_port")

    def get_camera_port(self) -> int:
        return self._get_property_if_exist("_camera_port")

    def get_config_colors_dict(self) -> ColorConfig:
        return self._get_property_if_exist("_color_config")

    def get_robot_color(self) -> Color:
        return self._get_property_if_exist("_selected_color")

    def get_configuration_file_path(self) -> Path:
        return self._get_property_if_exist("_configuration_file_path")

    def get_difficulty_level(self) -> int:
        return self._get_property_if_exist("_difficulty_level")

    def run(self) -> None:
        self._window.exec()
        self._stop_camera_preview()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    window = ConfigurationWindow()
    window.run()

    print(f"Camera port: {window.get_camera_port()}")
    print(f"Colors config: {window.get_config_colors_dict()}")
    print(f"File config: {window.get_configuration_file_path()}")
    print(f"Difficulty level: {window.get_difficulty_level()}")
    print(f"Robot color: {window.get_robot_color()}")
    print(f"Robot port: {window.get_robot_port()}")
