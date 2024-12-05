from src.GUI import game_window
from src.GUI.game_window import GameWindow
from src.GUI.init_window import ConfigurationWindow


def main() -> None:
    # config_window = ConfigurationWindow()
    # config_window.run()

    # print(
    #     f"{config_window.get_camera_port()=}\n{config_window.get_robot_port()=}\n{config_window.get_config_colors_dict()=}"
    # )

    # robot_color = config_window.get_robot_color()
    # robot_port = config_window.get_robot_port()
    # camera_port = config_window.get_camera_port()
    # color_config = config_window.get_config_colors_dict()

    # game_window = GameWindow(robot_color, robot_port, camera_port, color_config)
    game_window = GameWindow("", "", 2)
    game_window.run()


if __name__ == "__main__":
    main()
