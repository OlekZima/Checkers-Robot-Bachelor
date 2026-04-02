from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

import gradio as gr
import numpy as np

from src.checkers_game.checkers_game import CheckersGame
from src.checkers_game.negamax import NegamaxDecisionEngine
from src.common.enums import Color, Status


@dataclass
class _SessionState:
    game: CheckersGame
    robot_color: Color
    engine_depth: int


def _render_board_html(state: np.ndarray) -> str:
    symbols = {
        0: " ",
        1: "🟠",
        2: "🟠♛",
        -1: "🔵",
        -2: "🔵♛",
    }

    rows = []
    for y in range(8):
        cells = []
        for x in range(8):
            val = int(state[x][y])
            dark = (x + y) % 2 == 1
            bg = "#7f5f3a" if dark else "#d7c3a3"
            cell = (
                f'<td style="width:42px;height:42px;text-align:center;'
                f'font-size:24px;background:{bg};border:1px solid #333;">'
                f"{symbols[val]}</td>"
            )
            cells.append(cell)
        rows.append("<tr>" + "".join(cells) + "</tr>")

    return (
        '<div style="display:inline-block;border:2px solid #333;">'
        '<table style="border-collapse:collapse;">' + "".join(rows) + "</table></div>"
    )


def _status_text(game: CheckersGame, robot_color: Color, depth: int) -> str:
    turn = game.get_turn_of()
    status = game.get_status()
    winner = game.get_winning_player()
    points = game.get_points()

    if status == Status.IN_PROGRESS:
        status_s = "IN_PROGRESS"
    elif status == Status.DRAW:
        status_s = "DRAW"
    elif winner is None:
        status_s = "WON"
    else:
        status_s = f"WON ({winner.name})"

    return (
        f"Turn: {turn.name if turn else 'N/A'}\n"
        f"Status: {status_s}\n"
        f"Robot color: {robot_color.name}\n"
        f"Engine depth: {depth}\n"
        f"Score ORANGE: {points[Color.ORANGE]} | BLUE: {points[Color.BLUE]}"
    )


def _moves_text(game: CheckersGame) -> str:
    moves = game.get_possible_opts()
    if not moves:
        return "No legal moves."
    return "\n".join(str(m) for m in moves)


def _parse_move(text: str) -> list[int]:
    try:
        parsed = ast.literal_eval(text.strip())
    except Exception as exc:
        raise ValueError(f"Invalid move format: {exc}") from exc

    if not isinstance(parsed, list) or not all(isinstance(i, int) for i in parsed):
        raise ValueError("Move must be a list of ints, e.g. [21, 17].")
    if len(parsed) < 2:
        raise ValueError("Move must have at least 2 elements.")
    return parsed


def _new_state(robot_color: Color, depth: int) -> _SessionState:
    return _SessionState(
        game=CheckersGame(),
        robot_color=robot_color,
        engine_depth=max(1, int(depth)),
    )


def _refresh(s: _SessionState) -> tuple[str, str, str]:
    return (
        _render_board_html(s.game.get_game_state()),
        _status_text(s.game, s.robot_color, s.engine_depth),
        _moves_text(s.game),
    )


class GameWindow:
    """Compatibility wrapper for old constructor signature + Gradio runtime."""

    def __init__(
        self,
        robot_color: Color,
        robot_port: str | None = None,
        camera_port: int | None = None,
        color_config: dict | None = None,
        config_name: Path | None = None,
        depth_of_engine: int = 3,
    ) -> None:
        self.robot_color = robot_color
        self.depth_of_engine = depth_of_engine

        # Kept for compatibility with old call sites; intentionally unused.
        self.robot_port = robot_port
        self.camera_port = camera_port
        self.color_config = color_config
        self.config_name = config_name

        self._app: Optional[gr.Blocks] = None

    def _build_app(self) -> gr.Blocks:
        default_state = _new_state(self.robot_color, self.depth_of_engine)

        with gr.Blocks(title="Checkers Game (Gradio)") as app:
            gr.Markdown(
                "## Checkers Game (Logic-only)\n"
                "This view replaces the legacy desktop GUI and does not require robot/camera."
            )

            state = gr.State(default_state)

            with gr.Row():
                color_radio = gr.Radio(
                    choices=["ORANGE", "BLUE"],
                    value=self.robot_color.name,
                    label="Engine Color",
                )
                depth_slider = gr.Slider(
                    minimum=1,
                    maximum=8,
                    value=self.depth_of_engine,
                    step=1,
                    label="Engine Depth",
                )
                reset_btn = gr.Button("Reset Game")

            board = gr.HTML()
            summary = gr.Textbox(lines=5, label="Summary", interactive=False)
            legal_moves = gr.Textbox(lines=10, label="Legal Moves", interactive=False)

            with gr.Row():
                human_move = gr.Textbox(
                    label="Human Move",
                    placeholder="[21, 17] or [24, -20, 15]",
                )
                apply_human_btn = gr.Button("Apply Human Move")
                apply_engine_btn = gr.Button("Apply Engine Move")

            message = gr.Textbox(label="Message", interactive=False)

            def on_reset(color_name: str, depth: int):
                color = Color.ORANGE if color_name == "ORANGE" else Color.BLUE
                s = _new_state(color, depth)
                b, sm, mv = _refresh(s)
                return s, b, sm, mv, "Game reset."

            def on_apply_human(s: _SessionState, move_text: str):
                try:
                    move = _parse_move(move_text)
                    s.game.perform_move(move)
                    msg = f"Applied move: {move}"
                except Exception as exc:
                    msg = f"Move rejected: {exc}"
                b, sm, mv = _refresh(s)
                return s, b, sm, mv, msg

            def on_apply_engine(s: _SessionState, color_name: str, depth: int):
                s.robot_color = Color.ORANGE if color_name == "ORANGE" else Color.BLUE
                s.engine_depth = max(1, int(depth))

                if s.game.get_status() != Status.IN_PROGRESS:
                    b, sm, mv = _refresh(s)
                    return s, b, sm, mv, "Game already finished."

                if s.game.get_turn_of() != s.robot_color:
                    b, sm, mv = _refresh(s)
                    turn = s.game.get_turn_of()
                    return (
                        s,
                        b,
                        sm,
                        mv,
                        f"It is {turn.name if turn else 'N/A'} turn, engine is {s.robot_color.name}.",
                    )

                try:
                    engine = NegamaxDecisionEngine(
                        computer_color=s.robot_color, depth_to_use=s.engine_depth
                    )
                    chosen = engine.decide_move(s.game)
                    s.game.perform_move(chosen)
                    msg = f"Engine played: {chosen}"
                except Exception as exc:
                    msg = f"Engine failed: {exc}"

                b, sm, mv = _refresh(s)
                return s, b, sm, mv, msg

            # initial paint
            ib, isummary, imoves = _refresh(default_state)
            board.value = ib
            summary.value = isummary
            legal_moves.value = imoves

            reset_btn.click(
                on_reset,
                inputs=[color_radio, depth_slider],
                outputs=[state, board, summary, legal_moves, message],
            )

            apply_human_btn.click(
                on_apply_human,
                inputs=[state, human_move],
                outputs=[state, board, summary, legal_moves, message],
            )

            apply_engine_btn.click(
                on_apply_engine,
                inputs=[state, color_radio, depth_slider],
                outputs=[state, board, summary, legal_moves, message],
            )

        return app

    def run(self) -> None:
        self._app = self._build_app()
        self._app.launch()


def build_demo() -> gr.Blocks:
    """Convenience factory for external demo scripts/tests."""
    return GameWindow(robot_color=Color.ORANGE, depth_of_engine=3)._build_app()


if __name__ == "__main__":
    GameWindow(robot_color=Color.ORANGE, depth_of_engine=3).run()
