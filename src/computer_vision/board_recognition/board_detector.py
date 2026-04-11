"""Dependency-injected board detection service."""

from __future__ import annotations

from typing import Optional

import cv2 as cv
import numpy as np

from src.common.configs import RecognitionConfig
from src.common.exceptions import (
    BoardDetectionError,
    InsufficientDataError,
    NoStartTileError,
)

from .board import Board
from .contour_detector import ContourDetector


class BoardDetector:
    """Dependency-injected board detection service."""

    def __init__(
        self,
        contour_detector: Optional[ContourDetector] = None,
        recognition_config: Optional[RecognitionConfig] = None,
    ) -> None:
        """Initialize the detector with optional dependencies.

        Args:
            contour_detector: Pre-configured contour detector.
            recognition_config: Recognition configuration.
        """
        self.contour_detector = contour_detector or ContourDetector()
        self.recognition_config = recognition_config or RecognitionConfig()

    def detect(
        self, image: np.ndarray, recognition_config: Optional[RecognitionConfig] = None
    ) -> Board:
        """Detect the board in the given image.

        Args:
            image: Input BGR image.
            recognition_config: Optional configuration override.

        Returns:
            Detected Board instance.
        """
        config = recognition_config or self.recognition_config
        return Board.from_image(
            image=image,
            contour_detector=self.contour_detector,
            recognition_config=config,
        )


if __name__ == "__main__":
    cap = cv.VideoCapture(0)
    detector = BoardDetector()

    while True:
        ret, img = cap.read()
        if not ret:
            break

        try:
            board = detector.detect(img)
            print(f"Found tiles: {len(board.tiles)}")
            draw_image = board.get_frame_copy()
            cv.imshow("RESULT", draw_image)
        except (BoardDetectionError, InsufficientDataError, NoStartTileError) as exc:
            print(exc)

        if cv.waitKey(1) == ord("q"):
            break

    cap.release()
    cv.destroyAllWindows()
