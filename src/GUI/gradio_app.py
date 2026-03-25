from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Optional

import gradio as gr
import numpy as np

from src.checkers_game.checkers_game import CheckersGame
from src.checkers_game.negamax import NegamaxDecisionEngine
from src.common.enums import Color, Status


@dataclass
class AppSession:
    game: CheckersGame
    engine_color: Color
    engine_depth: int


def _color_from_label(label: str) -> Color:
    return Color.ORANGE if label.lower() == "orange" else Color.BLUE


def _status_text(status: Status, winner: Optional[Color]) -> str:
    if status == Status.IN_PROGRESS:
        return "IN_PROGRESS"
    if status == Status.DRAW:
        return "DRAW"
    if status == Status.WON:
        return f"WON ({winner.name})" if winner else "WON"
    return str(status)


def _render_board_html(state: np.ndarray) -> str:
    symbols = {
        0: " ",
        1: "🟠",
        2: "🟠Q",
        -1: "🔵",
        -2: "🔵Q",
    }

    rows = []
    for y in range(8):
        cells = []
        for x in range(8):
            val = int(state[x][y])
            dark = (x + y) % 2 == 1
            bg = "#6f4e37" if dark else "#d7c3a3"
            cell = (
                '<td style="width:42px;height:42px;text-align:center;'
                f'font-size:24px;border:1px solid #333;background:{bg};">'
                f"{symbols[val]}</td>"
            )
            cells.append(cell)
        rows.append("<tr>" + "".join(cells) + "</tr>")

    return (
        '<div style="display:inline-block;border:2px solid #333;border-radius:6px;overflow:hidden;">'
        '<table style="border-collapse:collapse;">' + "".join(rows) + "</table></div>"
    )


def _legal_moves_text(game: CheckersGame) -> str:
    opts = game.get_possible_opts()
    if not opts:
        return "No legal moves."
    return "\n".join(str(m) for m in opts)


def _summary(session: AppSession) -> str:
    game = session.game
    status = game.get_status()
    winner = game.get_winning_player()
    turn = game.get_turn_of()
    points = game.get_points()
    return (
        f"Turn: {turn.name if turn else 'N/A'}\n"
        f"Status: {_status_text(status, winner)}\n"
        f"Engine color: {session.engine_color.name}\n"
        f"Engine depth: {session.engine_depth}\n"
        f"Score — ORANGE: {points[Color.ORANGE]} | BLUE: {points[Color.BLUE]}"
    )


def _refresh(session: AppSession) -> tuple[str, str, str]:
    return (
        _render_board_html(session.game.get_game_state()),
        _summary(session),
        _legal_moves_text(session.game),
    )


def _new_game(
    engine_color_label: str, engine_depth: int
) -> tuple[AppSession, str, str, str, str]:
    session = AppSession(
        game=CheckersGame(),
        engine_color=_color_from_label(engine_color_label),
        engine_depth=max(1, int(engine_depth)),
    )
    board, summary, moves = _refresh(session)
    return session, board, summary, moves, "New game started."


def _parse_move(move_text: str) -> list[int]:
    try:
        parsed = ast.literal_eval(move_text.strip())
    except Exception as exc:  # noqa: BLE001
        raise ValueError(
            f"Invalid move syntax. Use e.g. [21, 17] or [24, -20, 15]. ({exc})"
        ) from exc

    if not isinstance(parsed, list) or not all(isinstance(i, int) for i in parsed):
        raise ValueError("Move must be a list of integers.")
    if len(parsed) < 2:
        raise ValueError("Move must include at least source and destination.")
    return parsed


def _apply_human_move(
    session: Optional[AppSession], move_text: str
) -> tuple[AppSession, str, str, str, str]:
    if session is None:
        return _new_game("Orange", 3)

    if session.game.get_status() != Status.IN_PROGRESS:
        board, summary, moves = _refresh(session)
        return session, board, summary, moves, "Game is finished. Start a new game."

    try:
        move = _parse_move(move_text)
        session.game.perform_move(move)
        msg = f"Applied human move: {move}"
    except Exception as exc:  # noqa: BLE001
        board, summary, moves = _refresh(session)
        return session, board, summary, moves, f"Move rejected: {exc}"

    board, summary, moves = _refresh(session)
    return session, board, summary, moves, msg


def _apply_engine_move(
    session: Optional[AppSession],
) -> tuple[AppSession, str, str, str, str]:
    if session is None:
        return _new_game("Orange", 3)

    game = session.game
    if game.get_status() != Status.IN_PROGRESS:
        board, summary, moves = _refresh(session)
        return session, board, summary, moves, "Game is finished. Start a new game."

    current_turn = game.get_turn_of()
    if current_turn != session.engine_color:
        board, summary, moves = _refresh(session)
        return (
            session,
            board,
            summary,
            moves,
            (
                "Engine move skipped: turn is "
                f"{current_turn.name if current_turn else 'N/A'}, "
                f"engine configured for {session.engine_color.name}."
            ),
        )

    try:
        engine = NegamaxDecisionEngine(
            computer_color=session.engine_color,
            depth_to_use=session.engine_depth,
        )
        move = engine.decide_move(game)
        game.perform_move(move)
        msg = f"Engine played: {move}"
    except Exception as exc:  # noqa: BLE001
        board, summary, moves = _refresh(session)
        return session, board, summary, moves, f"Engine failed: {exc}"

    board, summary, moves = _refresh(session)
    return session, board, summary, moves, msg


def _set_engine(
    session: Optional[AppSession], engine_color_label: str, engine_depth: int
) -> tuple[AppSession, str]:
    if session is None:
        session = AppSession(
            game=CheckersGame(),
            engine_color=_color_from_label(engine_color_label),
            engine_depth=max(1, int(engine_depth)),
        )
    else:
        session.engine_color = _color_from_label(engine_color_label)
        session.engine_depth = max(1, int(engine_depth))

    return (
        session,
        f"Engine updated: color={session.engine_color.name}, depth={session.engine_depth}",
    )


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Checkers Gradio App (Logic Only)") as demo:
        gr.Markdown(
            "## Checkers — Gradio GUI (Logic-only)\n"
            "- No robot required\n"
            "- No camera required\n"
            "- Enter moves as Python lists, e.g. `[21, 17]` or `[24, -20, 15]`"
        )

        session_state = gr.State(value=None)

        with gr.Row():
            engine_color = gr.Radio(
                choices=["Orange", "Blue"],
                value="Orange",
                label="Engine Color",
            )
            engine_depth = gr.Slider(
                minimum=1,
                maximum=8,
                step=1,
                value=3,
                label="Engine Depth",
            )

        with gr.Row():
            btn_new = gr.Button("Start / Reset")
            btn_engine = gr.Button("Apply Engine Move")
            btn_engine_set = gr.Button("Update Engine Settings")

        board_view = gr.HTML(label="Board")
        summary_box = gr.Textbox(label="Game Summary", lines=5, interactive=False)
        legal_moves_box = gr.Textbox(
            label="Legal Moves (Current Turn)",
            lines=10,
            interactive=False,
        )

        with gr.Row():
            move_input = gr.Textbox(
                label="Human Move",
                placeholder="[21, 17]",
            )
            btn_human = gr.Button("Apply Human Move")

        message_box = gr.Textbox(label="Message", interactive=False)

        btn_new.click(
            fn=_new_game,
            inputs=[engine_color, engine_depth],
            outputs=[
                session_state,
                board_view,
                summary_box,
                legal_moves_box,
                message_box,
            ],
        )

        btn_human.click(
            fn=_apply_human_move,
            inputs=[session_state, move_input],
            outputs=[
                session_state,
                board_view,
                summary_box,
                legal_moves_box,
                message_box,
            ],
        )

        btn_engine.click(
            fn=_apply_engine_move,
            inputs=[session_state],
            outputs=[
                session_state,
                board_view,
                summary_box,
                legal_moves_box,
                message_box,
            ],
        )

        btn_engine_set.click(
            fn=_set_engine,
            inputs=[session_state, engine_color, engine_depth],
            outputs=[session_state, message_box],
        )

    return demo


def create_demo() -> gr.Blocks:
    return build_demo()


def create_app() -> gr.Blocks:
    return build_demo()


def main() -> None:
    app = build_demo()
    app.launch()


if __name__ == "__main__":
    main()
