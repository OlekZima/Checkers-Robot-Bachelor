from src.GUI.game_window import GameWindow
from src.GUI.init_window import ConfigurationWindow


def main() -> None:
    # config_window = ConfigurationWindow()
    # config_window.run()

    # print(
    #     f"{config_window.get_camera_port()=}\n{config_window.get_robot_port()=}\n{config_window.get_config_colors_dict()=}"
    # )

    game_window = GameWindow("", "")
    game_window.run()

if __name__ == "__main__":
    main()
