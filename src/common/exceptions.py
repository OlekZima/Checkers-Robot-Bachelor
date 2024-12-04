"""Module provides custom exceptions for the project."""


class BoardError(Exception):
    """General exception for board errors."""


class NoStartTileError(BoardError):
    """Exception raised when no static tile is found."""


class BoardDetectionError(BoardError):
    """Exception raised when board detection fails."""


class InsufficientDataError(BoardError):
    """Exception raised when there is insufficient data to process Board."""


class BoardMappingError(BoardError):
    """Exception raised when there is an error in mapping the board."""


class CV2Error(Exception):
    """General exception for OpenCV errors."""


class CameraReadError(CV2Error):
    """Exception raised when VideoCapture.read() fails."""


class DecisionEngineError(Exception):
    """General exception for decision engine errors."""


class DobotError(Exception):
    """General exception for Dobot errors."""
