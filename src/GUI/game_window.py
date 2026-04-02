from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)

from src.checkers_game.game_controller import GameController
from src.common.configs import ColorConfig
from src.common.enums import Color, GameStateResult, RobotGameReportItem, Status
from src.common.utils import CONFIG_PATH
from src.computer_vision.board_recognition.contours import ContourDetector
from src.computer_vision.game_state_recognition import GameState
from src.robot_manipulation.dobot_controller import DobotController


class GameWindow:
    def __init__(
        self,
        robot_color: Color,
        robot_port: str,
        camera_port: int,
        color_config: ColorConfig,
        config_name: str | Path,
        depth_of_engine: int = 3,
    ) -> None:
        self._camera_port = camera_port
        self._cap = cv2.VideoCapture(self._camera_port)

        self._game = GameController(robot_color, depth_of_engine)
        self._dobot = DobotController(robot_color, CONFIG_PATH / config_name, robot_port)
        self._device = self._dobot.device
        self._board_recognition = GameState(color_config)

        self._app = QApplication.instance() or QApplication([])
        self._window = QMainWindow()
        self._window.setWindowTitle("Checkers Game")
        self._window.setMinimumSize(1320, 900)

        self._main_camera_view = QLabel()
        self._main_camera_view.setFixedSize(640, 480)
        self._main_camera_view.setStyleSheet("background-color: black;")
        self._main_camera_view.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._move_image = QLabel()
        self._move_image.setFixedSize(200, 200)
        self._move_image.setStyleSheet("background-color: blue;")
        self._move_image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._move_status = QLabel("")
        self._move_status.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._move_status.setWordWrap(True)

        self._output_view = QPlainTextEdit()
        self._output_view.setReadOnly(True)
        self._output_view.setFixedWidth(320)

        self._dilate_view = QLabel()
        self._dilate_view.setFixedSize(640, 480)
        self._dilate_view.setStyleSheet("background-color: red;")
        self._dilate_view.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._board_view = QLabel()
        self._board_view.setFixedSize(640, 480)
        self._board_view.setStyleSheet("background-color: black;")
        self._board_view.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._game_state_view = QLabel()
        self._game_state_view.setFixedSize(500, 500)
        self._game_state_view.setStyleSheet("background-color: white;")
        self._game_state_view.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._timer = QTimer(self._window)
        self._timer.timeout.connect(self._process_frame)
        self._frame_skip = 20

        self._setup_ui()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self._window.setCentralWidget(central_widget)

        tab_widget = QTabWidget()
        tab_widget.addTab(self._create_game_tab(), "Game")
        tab_widget.addTab(self._create_additional_views_tab(), "Additional views")

        layout = QVBoxLayout(central_widget)
        layout.addWidget(tab_widget)

    def _create_game_tab(self) -> QWidget:
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
        container = QWidget()
        layout = QHBoxLayout(container)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self._dilate_view)
        left_layout.addWidget(self._board_view)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self._game_state_view)
        right_layout.addStretch()

        layout.addLayout(left_layout)
        layout.addLayout(right_layout)

        return container

    def _convert_frame_to_pixmap(self, frame: np.ndarray) -> QPixmap:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb_frame.shape
        bytes_per_line = channel * width
        q_image = QImage(
            rgb_frame.data.tobytes(),
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )
        return QPixmap.fromImage(q_image)

    def _update_graph(self, frame: np.ndarray, label: QLabel) -> None:
        if frame is None or frame.size == 0:
            return
        pixmap = self._convert_frame_to_pixmap(frame)
        label.setPixmap(
            pixmap.scaled(
                label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _process_frame(self) -> None:
        if self._cap is None or not self._cap.isOpened():
            return

        ret, image = self._cap.read()
        if not ret or image is None:
            return

        if self._frame_skip > 0:
            self._frame_skip -= 1
            return

        self._update_graph(image, self._main_camera_view)

        try:
            _, game_state = self._board_recognition.update_game_state(image)
            update_game_state_result = self._game.update_game_state(game_state)

            self._game_state_image = self._board_recognition.get_game_state_image()
            self._update_graph(self._game_state_image, self._game_state_view)

            self._board_image = self._board_recognition.get_board_image()
            self._update_graph(self._board_image, self._board_view)

            dilate_image = ContourDetector.image_dil
            if dilate_image is not None:
                self._update_graph(dilate_image, self._dilate_view)

            if update_game_state_result in (
                GameStateResult.INVALID_OPPONENT_MOVE,
                GameStateResult.INVALID_ROBOT_MOVE,
            ):
                self._move_status.setText("Invalid move! Please correct it.")
                return

            if update_game_state_result == GameStateResult.VALID_WRONG_ROBOT_MOVE:
                self._move_status.setText("Wrong robot move! Please correct it.")
                return

            game_state_report = self._game.report_state()
            status = game_state_report.get(RobotGameReportItem.STATUS)
            if status != Status.IN_PROGRESS:
                if status == Status.DRAW:
                    self._move_status.setText("Game Over - DRAW!")
                elif game_state_report.get(RobotGameReportItem.WINNER) == Color.BLUE:
                    self._move_status.setText("Game Over - ROBOT WON!")
                else:
                    self._move_status.setText("Game Over - OPPONENT WON!")
                self._timer.stop()
                self._window.close()
                return

            if (
                game_state_report.get(RobotGameReportItem.TURN_OF)
                == game_state_report.get(RobotGameReportItem.ROBOT_COLOR)
            ):
                self._move_status.setText("Robot's turn...")
                self._dobot.perform_move(
                    game_state_report.get(RobotGameReportItem.ROBOT_MOVE),
                    is_crown=game_state_report.get(RobotGameReportItem.IS_CROWNED, False),
                )
                self._frame_skip = 20
            else:
                self._move_status.setText("Player's turn...")
        except Exception as error:
            self._output_view.appendPlainText(f"Error: {error}")

    def run(self) -> None:
        self._window.show()
        self._timer.start(30)
        self._app.exec()
        if self._cap is not None:
            self._cap.release()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    color_config = ColorConfig(
        {
            "orange": (220, 70, 0),
            "blue": (42, 113, 157),
            "black": (107, 108, 101),
            "white": (198, 205, 203),
        }
    )
    window = GameWindow(Color.ORANGE, "/dev/ttyUSB0", 2, color_config, "guit_test_2.txt")
    window.run()
