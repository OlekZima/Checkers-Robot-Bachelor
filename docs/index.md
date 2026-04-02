# Checkers Robot Bachelor

> An autonomous checkers-playing robot system integrating computer vision, game AI, and robotic arm manipulation.

## Overview

This project implements a complete autonomous checkers game system that combines:

- **Computer Vision** — Real-time board detection, tile recognition, and checker piece identification
- **Game Logic** — Full checkers rule implementation with move validation and state management
- **AI Decision Engine** — Negamax algorithm with alpha-beta pruning for optimal move selection
- **Robot Manipulation** — Dobot robotic arm control for physical piece movement
- **GUI Interface** — PyQt6-based application for configuration, calibration, and game monitoring

## Quick Start

### Prerequisites

```bash
# Install dependencies
uv sync

# Run type checking
uvx ty check
```

### Running the Application

```bash
# Launch the configuration and calibration window
uv run -m src.GUI.init_window

# Launch the game window (requires calibration)
uv run -m src.GUI.game_window
```

## Project Structure

```
src/
├── checkers_game/          # Game logic and AI
│   ├── checkers_game.py    # Core game rules and state
│   ├── game_controller.py  # Game flow coordination
│   └── negamax.py          # AI decision engine
├── common/                 # Shared utilities
│   ├── configs/            # Configuration types
│   ├── enums/              # Enumeration types
│   ├── exceptions/         # Custom exception hierarchy
│   └── utils.py            # Helper functions
├── computer_vision/        # Vision processing
│   ├── board_recognition/  # Board and tile detection
│   ├── checker.py          # Checker piece model
│   ├── checker_detector.py # Checker detection logic
│   └── game_state_recognition.py  # Game state visualization
├── robot_manipulation/     # Robot arm control
│   ├── robot_arm.py        # Hardware abstraction
│   ├── dobot_arm.py        # Dobot implementation
│   ├── move_executor.py    # Movement sequences
│   ├── king_manager.py     # King piece handling
│   ├── robot_manipulator.py # Main facade
│   └── calibration_controller.py  # Calibration workflow
└── GUI/                    # User interface
    ├── init_window.py      # Configuration & calibration
    └── game_window.py      # Main game interface
```

## Documentation

### Core Modules

| Module | Description |
|--------|-------------|
| [Checkers Game](api/checkers_game.md) | Game rules, state management, and move validation |
| [Game Controller](api/game_controller.md) | Coordinates game flow between CV, AI, and robot |
| [Negamax Engine](api/negamax.md) | AI decision making with alpha-beta pruning |

### Computer Vision

| Module | Description |
|--------|-------------|
| [Contour Detector](api/contour_detector.md) | Board contour detection and preprocessing |
| [Board Tile](api/board_tile.md) | Individual tile representation |
| [Tile Grid](api/tile_grid.md) | Tile collection and neighbor management |
| [Board](api/board.md) | Complete board detection and point interpolation |
| [Board Detector](api/board_detector.md) | High-level board detection facade |
| [Checker](api/checker.md) | Checker piece data model |
| [Checker Detector](api/checker_detector.md) | Vectorized checker color detection |
| [Game State Recognition](api/game_state_recognition.md) | Game state visualization and tracking |

### Robot Manipulation

| Module | Description |
|--------|-------------|
| [Robot Arm](api/robot_arm.md) | Abstract hardware interface |
| [Dobot Arm](api/dobot_arm.md) | Dobot Magician implementation |
| [Move Executor](api/move_executor.md) | Piece movement sequences |
| [King Manager](api/king_manager.md) | King piece inventory and placement |
| [Robot Manipulator](api/robot_manipulator.md) | Main robot control facade |
| [Calibration Controller](api/calibration_controller.md) | Arm calibration workflow |
| [Calibration Data](api/calibration_data.md) | Calibrated position storage |
| [Calibration File Handler](api/calibration_file_handler.md) | Calibration file I/O |

### Common Utilities

| Module | Description |
|--------|-------------|
| [Configs](api/configs.md) | Configuration dataclasses and typed dicts |
| [Enums](api/enums.md) | Enumeration types for game state |
| [Exceptions](api/exceptions.md) | Custom exception hierarchy |
| [Utils](api/utils.md) | Coordinate conversion and math utilities |

### GUI

| Module | Description |
|--------|-------------|
| [Game Window](api/game_window.md) | Main game interface |
| [Init Window](api/init_window.md) | Configuration and calibration interface |

## Architecture

### System Flow

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Camera    │────▶│ Computer Vision  │────▶│ Game State   │
│   Input     │     │ (Board/Checker)  │     │ Recognition  │
└─────────────┘     └──────────────────┘     └──────┬───────┘
                                                     │
┌─────────────┐     ┌──────────────────┐     ┌──────▼───────┐
│   Dobot     │◀────│ Robot            │◀────│ Game         │
│   Arm       │     │ Manipulation     │     │ Controller   │
└─────────────┘     └──────────────────┘     └──────┬───────┘
                                                     │
                                              ┌──────▼───────┐
                                              │ Negamax AI   │
                                              │ Engine       │
                                              └──────────────┘
```

### Design Principles

- **Single Responsibility** — Each class has one clear purpose
- **Dependency Injection** — Components receive dependencies explicitly
- **Hardware Abstraction** — Robot control through abstract interfaces
- **Type Safety** — Full type hints with `ty` static analysis
- **Backward Compatibility** — Legacy imports supported via re-exports

## Development

### Type Checking

```bash
uvx ty check
```

### Code Style

The project follows PEP 8 conventions with:
- Type hints on all functions and methods
- Google-style docstrings for mkdocstrings compatibility
- One class per file (except tightly coupled pairs)
- Descriptive naming over abbreviations

## License

This project is part of a bachelor's degree program.