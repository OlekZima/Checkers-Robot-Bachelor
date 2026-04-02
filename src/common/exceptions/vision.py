"""Computer vision exceptions."""

from __future__ import annotations

__all__ = [
    "CV2Error",
    "CameraReadError",
]


class CV2Error(Exception):
    """Base exception for computer vision and OpenCV-related errors."""


class CameraReadError(CV2Error):
    """Raised when reading a frame from the camera fails."""
