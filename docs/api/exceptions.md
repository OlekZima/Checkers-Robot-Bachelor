# Exceptions

Custom exception hierarchy for the checkers robot project.

This module defines all custom exceptions used throughout the application, organized by subsystem for clarity and maintainability.

## API Reference

### Board Exceptions

::: src.common.exceptions.board.BoardError
    options:
      show_root_heading: true
      show_source: true
      members: true
      inherited_members: true
      heading_level: 3

::: src.common.exceptions.board.NoStartTileError
    options:
      show_root_heading: true
      show_source: true
      members: true
      inherited_members: true
      heading_level: 3

::: src.common.exceptions.board.BoardDetectionError
    options:
      show_root_heading: true
      show_source: true
      members: true
      inherited_members: true
      heading_level: 3

::: src.common.exceptions.board.InsufficientDataError
    options:
      show_root_heading: true
      show_source: true
      members: true
      inherited_members: true
      heading_level: 3

::: src.common.exceptions.board.BoardMappingError
    options:
      show_root_heading: true
      show_source: true
      members: true
      inherited_members: true
      heading_level: 3

### Vision Exceptions

::: src.common.exceptions.vision.CV2Error
    options:
      show_root_heading: true
      show_source: true
      members: true
      inherited_members: true
      heading_level: 3

::: src.common.exceptions.vision.CameraReadError
    options:
      show_root_heading: true
      show_source: true
      members: true
      inherited_members: true
      heading_level: 3

### Game Exceptions

::: src.common.exceptions.game.CheckersError
    options:
      show_root_heading: true
      show_source: true
      members: true
      inherited_members: true
      heading_level: 3

::: src.common.exceptions.game.CheckersGameEndError
    options:
      show_root_heading: true
      show_source: true
      members: true
      inherited_members: true
      heading_level: 3

::: src.common.exceptions.game.CheckersGameNotPermittedMoveError
    options:
      show_root_heading: true
      show_source: true
      members: true
      inherited_members: true
      heading_level: 3

### Decision Engine Exceptions

::: src.common.exceptions.decision.DecisionEngineError
    options:
      show_root_heading: true
      show_source: true
      members: true
      inherited_members: true
      heading_level: 3

### Robot Exceptions

::: src.common.exceptions.robot.DobotError
    options:
      show_root_heading: true
      show_source: true
      members: true
      inherited_members: true
      heading_level: 3