from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import gradio as gr
from serial.tools import list_ports

from src.common.configs import ColorConfig
from src.common.enums import Color


@dataclass
class _ConfigState:
    robot_color: Optional[Color] = None
    difficulty_level: int = 3
    robot_port: Optional[str] = None
    camera_port: Optional[int] = None
    configuration_file_path: Optional[Path] = None
    color_config: ColorConfig | None = None
    completed: bool = False


def _default_color_config() -> ColorConfig:
    return {
        "orange": (220, 70, 0),
        "blue": (42, 113, 157),
        "black": (107, 108, 101),
        "white": (198, 205, 203),
    }


class ConfigurationWindow:
    """Compatibility adapter with Gradio backend.

    Public API matches the old class:
    - run()
    - get_robot_port()
    - get_camera_port()
    - get_config_colors_dict()
    - get_robot_color()
    - get_configuration_file_path()
    - get_difficulty_level()
    """

    def __init__(self) -> None:
        self._state = _ConfigState(color_config=_default_color_config())
        self._app: Optional[gr.Blocks] = None

    def _get_property_if_exist(self, name: str):
        value = getattr(self._state, name)
        if value is None:
            raise AttributeError(
                f"No {name} property!\nLooks like you didn't complete the `run` flow."
            )
        return value

    def get_robot_port(self) -> str:
        return self._get_property_if_exist("robot_port")

    def get_camera_port(self) -> int:
        return self._get_property_if_exist("camera_port")

    def get_config_colors_dict(self) -> dict[str, tuple[int, int, int]]:
        return self._get_property_if_exist("color_config")

    def get_robot_color(self) -> Color:
        return self._get_property_if_exist("robot_color")

    def get_configuration_file_path(self) -> Path:
        return self._get_property_if_exist("configuration_file_path")

    def get_difficulty_level(self) -> int:
        return self._get_property_if_exist("difficulty_level")

    @staticmethod
    def _list_robot_ports() -> list[str]:
        ports = []
        for p in list_ports.comports():
            # keep compact "device - description" format
            desc = p.description if p.description else "Unknown"
            ports.append(f"{p.device} - {desc}")
        return ports if ports else ["(no serial ports detected)"]

    @staticmethod
    def _normalize_robot_port(port_choice: str) -> Optional[str]:
        if not port_choice or port_choice.startswith("(no serial ports"):
            return None
        # stored value is only device path
        return port_choice.split(" - ", 1)[0]

    @staticmethod
    def _parse_camera_port(raw: str) -> Optional[int]:
        raw = (raw or "").strip()
        if raw == "":
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    @staticmethod
    def _map_color(label: str) -> Optional[Color]:
        if not label:
            return None
        if label.lower() == "orange":
            return Color.ORANGE
        if label.lower() == "blue":
            return Color.BLUE
        return None

    @staticmethod
    def _validate_config_file(file_obj) -> tuple[Optional[Path], Optional[str]]:
        if file_obj is None:
            return None, "Please upload/select a calibration config file."
        path = Path(file_obj.name)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return None, f"Failed to read config file: {exc}"

        if len(lines) != 42:
            return None, f"Invalid config file: expected 42 lines, got {len(lines)}"
        return path, None

    def _build_app(self) -> gr.Blocks:
        with gr.Blocks(title="Checkers Robot Configuration (Gradio)") as app:
            gr.Markdown(
                "## Checkers Robot Configuration\n"
                "This replaces the legacy desktop configuration window."
            )

            state = gr.State(value=self._state)

            with gr.Row():
                robot_color = gr.Radio(
                    choices=["Orange", "Blue"], label="Robot Color", value="Orange"
                )
                difficulty = gr.Slider(
                    minimum=1, maximum=10, value=3, step=1, label="Difficulty"
                )

            with gr.Row():
                robot_port = gr.Dropdown(
                    choices=self._list_robot_ports(),
                    value=None,
                    label="Robot Port",
                    allow_custom_value=False,
                )
                camera_port = gr.Textbox(
                    label="Camera Port (integer)", value="0", placeholder="e.g. 0"
                )

            config_file = gr.File(
                label="Calibration Config File (.txt)",
                file_types=[".txt"],
                type="filepath",
            )

            # Optional manual color setup (RGB tuples as text)
            with gr.Accordion("Advanced: Color config (RGB tuples)", open=False):
                orange_rgb = gr.Textbox(label="Orange", value="220,70,0")
                blue_rgb = gr.Textbox(label="Blue", value="42,113,157")
                black_rgb = gr.Textbox(label="Black", value="107,108,101")
                white_rgb = gr.Textbox(label="White", value="198,205,203")

            output = gr.Textbox(label="Status", lines=5, interactive=False)
            complete = gr.Button("Save configuration")

            def _parse_rgb(
                raw: str, fallback: tuple[int, int, int]
            ) -> tuple[int, int, int]:
                parts = [p.strip() for p in (raw or "").split(",")]
                if len(parts) != 3:
                    return fallback
                try:
                    vals = tuple(int(v) for v in parts)
                except ValueError:
                    return fallback
                if any(v < 0 or v > 255 for v in vals):
                    return fallback
                return vals  # type: ignore[return-value]

            def on_complete(
                st: _ConfigState,
                rc_label: str,
                diff: int,
                rp: str,
                cp: str,
                cfg,
                o: str,
                b: str,
                k: str,
                w: str,
            ):
                color = self._map_color(rc_label)
                if color is None:
                    return st, "Select a valid robot color."

                robot_dev = self._normalize_robot_port(rp)
                if robot_dev is None:
                    return st, "Select a valid robot port."

                cam = self._parse_camera_port(cp)
                if cam is None:
                    return st, "Camera port must be an integer."

                cfg_path, cfg_err = self._validate_config_file(cfg)
                if cfg_err is not None:
                    return st, cfg_err

                st.robot_color = color
                st.difficulty_level = int(diff)
                st.robot_port = robot_dev
                st.camera_port = cam
                st.configuration_file_path = cfg_path
                st.color_config = {
                    "orange": _parse_rgb(o, (220, 70, 0)),
                    "blue": _parse_rgb(b, (42, 113, 157)),
                    "black": _parse_rgb(k, (107, 108, 101)),
                    "white": _parse_rgb(w, (198, 205, 203)),
                }
                st.completed = True

                msg = (
                    "Configuration saved.\n"
                    f"- robot_color: {st.robot_color.name}\n"
                    f"- difficulty: {st.difficulty_level}\n"
                    f"- robot_port: {st.robot_port}\n"
                    f"- camera_port: {st.camera_port}\n"
                    f"- config_file: {st.configuration_file_path}"
                )
                return st, msg

            complete.click(
                fn=on_complete,
                inputs=[
                    state,
                    robot_color,
                    difficulty,
                    robot_port,
                    camera_port,
                    config_file,
                    orange_rgb,
                    blue_rgb,
                    black_rgb,
                    white_rgb,
                ],
                outputs=[state, output],
            )

            # keep state synced to instance on every completion click
            def _sync_to_instance(st: _ConfigState):
                self._state = st
                return "Configuration captured in adapter state."

            complete.click(fn=_sync_to_instance, inputs=[state], outputs=[output])

        return app

    def run(self) -> None:
        """Launch Gradio config UI.

        Note:
        - In Gradio this is web-based and non-blocking from a data workflow
          perspective; you finalize config by clicking "Save configuration".
        - Existing callers can still call getters afterwards if this adapter
          instance remains alive in-process.
        """
        self._app = self._build_app()
        self._app.launch()


def build_demo() -> gr.Blocks:
    """Convenience helper to expose config-only demo app."""
    return ConfigurationWindow()._build_app()


def main() -> None:
    ConfigurationWindow().run()


if __name__ == "__main__":
    main()
