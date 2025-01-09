from src.GUI.game_window import GameWindow
from src.GUI.init_window import ConfigurationWindow


def main() -> None:
    config_window = ConfigurationWindow()
    config_window.run()

    game_window = GameWindow(
        config_window.get_robot_color(),
        config_window.get_robot_port(),
        config_window.get_camera_port(),
        config_window.get_config_colors_dict(),
        config_window.get_configuration_file_path(),
        config_window.get_difficulty_level(),
    )
    game_window.run()


if __name__ == "__main__":
    main()
