"""Game window module for the checkers robot GUI.

This module provides the main game interface, integrating computer vision,
game logic, and robot manipulation into a cohesive PyQt6 application.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, cast

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.checkers_game.game_controller import GameController
from src.common.configs import ColorConfig
from src.common.enums import Color, GameReportField, GameStatus, MoveValidationResult
from src.common.utils import CONFIG_PATH
from src.computer_vision.game_state_recognition import GameState
from src.robot_manipulation.robot_manipulator import RobotManipulator


class GameWindow:
    """Main game window integrating CV, game logic, and robot control."""

    def __init__(
        self,
        robot_color: Color,
        robot_port: str,
        camera_port: int,
        color_config: ColorConfig,
        config_name: str | Path,
        engine_depth: int = 3,
    ) -> None:
        """Initialize the game window.

        Args:
            robot_color: Color assigned to the robot player.
            robot_port: Serial port for the robot arm.
            camera_port: Camera device index.
            color_config: Color configuration for detection.
            config_name: Calibration configuration filename.
            engine_depth: Search depth for the AI engine.
        """
        self._camera_port = camera_port
        self._cap: Optional[cv2.VideoCapture] = cv2.VideoCapture(self._camera_port)

        self._game = GameController(robot_color, engine_depth)
        self._robot = RobotManipulator(
            port=robot_port,
            config_path=CONFIG_PATH,
            robot_color=robot_color,
            config_filename=str(config_name).removesuffix(".txt")
            if isinstance(config_name, str)
            else config_name.stem,
        )
        self._board_recognition = GameState(color_config)

        # Qt application setup
        self._app = QApplication.instance() or QApplication([])
        self._window = QMainWindow()
        self._window.setWindowTitle("Checkers Game")
        self._window.setMinimumSize(1320, 900)

        # UI components
        self._main_camera_view = self._create_image_label(640, 480, "black")
        self._move_image = self._create_image_label(200, 200, "blue")
        self._move_status = self._create_status_label()
        self._output_view = self._create_output_view()
        self._board_view = self._create_image_label(640, 480, "black")
        self._game_state_view = self._create_image_label(500, 500, "white")

        # Frame processing
        self._timer = QTimer(self._window)
        self._timer.timeout.connect(self._process_frame)
        self._frame_skip = 20

        self._setup_ui()

    def _create_image_label(self, width: int, height: int, bg_color: str) -> QLabel:
        """Create a QLabel for displaying images.

        Args:
            width: Label width.
            height: Label height.
            bg_color: Background color name.

        Returns:
            Configured QLabel instance.
        """
        label = QLabel()
        label.setFixedSize(width, height)
        label.setStyleSheet(f"background-color: {bg_color};")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def _create_status_label(self) -> QLabel:
        """Create a label for displaying move status messages."""
        label = QLabel("")
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        label.setWordWrap(True)
        return label

    def _create_output_view(self) -> QPlainTextEdit:
        """Create a read-only text output view."""
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setFixedWidth(320)
        return view

    def _setup_ui(self) -> None:
        """Set up the main window layout with tabs."""
        central_widget = QWidget()
        self._window.setCentralWidget(central_widget)

        tab_widget = QTabWidget()
        tab_widget.addTab(self._create_game_tab(), "Game")
        tab_widget.addTab(self._create_additional_views_tab(), "Additional Views")

        layout = QVBoxLayout(central_widget)
        layout.addWidget(tab_widget)

    def _create_game_tab(self) -> QWidget:
        """Create the main game tab with camera and status views."""
        container = QWidget()
        layout = QHBoxLayout(container)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self._main_camera_view)
        left_layout.addWidget(self._move_image, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self._move_status)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self._output_view)
        right_layout.addStretch()

        layout.addLayout(left_layout)
        layout.addLayout(right_layout)
        return container

    def _create_additional_views_tab(self) -> QWidget:
        """Create the tab with board and game state views."""
        container = QWidget()
        layout = QHBoxLayout(container)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self._board_view)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self._game_state_view)
        right_layout.addStretch()

        layout.addLayout(left_layout)
        layout.addLayout(right_layout)
        return container

    def _convert_frame_to_pixmap(self, frame: np.ndarray) -> Optional[QPixmap]:
        """Convert a NumPy BGR frame to a QPixmap.

        Args:
            frame: BGR image array.

        Returns:
            QPixmap or None if conversion fails.
        """
        if frame is None or frame.size == 0:
            return None

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb_frame.shape
        bytes_per_line = channels * width

        q_image = QImage(
            rgb_frame.data.tobytes(),
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )
        return QPixmap.fromImage(q_image)

    def _update_display(self, frame: np.ndarray, label: QLabel) -> None:
        """Update a QLabel with a new frame.

        Args:
            frame: BGR image array.
            label: Target QLabel.
        """
        pixmap = self._convert_frame_to_pixmap(frame)
        if pixmap is not None:
            label.setPixmap(
                pixmap.scaled(
                    label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def _process_frame(self) -> None:
        """Process a single camera frame and update game state."""
        if self._cap is None or not self._cap.isOpened():
            return

        ret, image = self._cap.read()
        if not ret or image is None:
            return

        if self._frame_skip > 0:
            self._frame_skip -= 1
            return

        self._update_display(image, self._main_camera_view)

        try:
            # Update board recognition and game state
            _, game_state = self._board_recognition.update(image)
            validation_result = self._game.update_game_state(game_state)

            # Update game state visualization
            game_state_image = self._board_recognition.render_board()
            self._update_display(game_state_image, self._game_state_view)

            # Update board detection view
            board_image = self._board_recognition.get_last_detected_frame()
            self._update_display(board_image, self._board_view)

            # Handle validation results
            if validation_result in (
                MoveValidationResult.INVALID_OPPONENT_MOVE,
                MoveValidationResult.INVALID_ROBOT_MOVE,
            ):
                self._move_status.setText("Invalid move! Please correct it.")
                return

            if validation_result == MoveValidationResult.VALID_WRONG_ROBOT_MOVE:
                self._move_status.setText("Wrong robot move! Please correct it.")
                return

            # Check game status
            report = self._game.generate_report()
            status = cast(GameStatus, report.get(GameReportField.STATUS))

            if status != GameStatus.IN_PROGRESS:
                self._handle_game_end(status, report)
                return

            # Handle robot's turn
            turn_of = report.get(GameReportField.TURN_OF)
            robot_color = report.get(GameReportField.ROBOT_COLOR)

            if turn_of == robot_color:
                self._move_status.setText("Robot's turn...")
                robot_move = report.get(GameReportField.ROBOT_MOVE)
                is_crowning = bool(report.get(GameReportField.IS_CROWNED, False))

                if robot_move is not None:
                    self._robot.execute_move(
                        cast(List[int], robot_move), is_crown=is_crowning
                    )

                self._frame_skip = 20
            else:
                self._move_status.setText("Player's turn...")

        except Exception as error:
            self._output_view.appendPlainText(f"Error: {error}")

    def _handle_game_end(
        self, status: GameStatus, report: dict[GameReportField, object]
    ) -> None:
        """Handle game end conditions.

        Args:
            status: Final game status.
            report: Game state report.
        """
        if status == GameStatus.DRAW:
            self._move_status.setText("Game Over - DRAW!")
        elif report.get(GameReportField.WINNER) == Color.BLUE:
            self._move_status.setText("Game Over - ROBOT WON!")
        else:
            self._move_status.setText("Game Over - OPPONENT WON!")

        self._timer.stop()
        self._window.close()

    def run(self) -> None:
        """Start the game window and event loop."""
        self._window.show()
        self._timer.start(30)
        self._app.exec()

        if self._cap is not None:
            self._cap.release()


if __name__ == "__main__":
    color_config = ColorConfig(
        {
            "orange": (220, 70, 0),
            "blue": (42, 113, 157),
            "black": (107, 108, 101),
            "white": (198, 205, 203),
        }
    )
    window = GameWindow(
        robot_color=Color.ORANGE,
        robot_port="/dev/ttyUSB0",
        camera_port=2,
        color_config=color_config,
        config_name="gui_test_2.txt",
    )
    window.run()
