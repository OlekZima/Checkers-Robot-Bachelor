import sys
import termios
from checkers_game_and_decissions.checkers_game import Color


def get_coord_from_field_id(field_id: int, color: Color = None) -> tuple[int, int]:
    y, x = divmod((field_id - 1), 4)
    x *= 2

    if y % 2 == 0:
        x += 1

    if color == Color.ORANGE:
        y = 7 - y
        x = 7 - x

    return x, y


def get_field_id_from_coord(x_cord: float, y_cord: float) -> int:
    id = y_cord * 4 + 1

    if y_cord % 2 == 1:
        id += x_cord / 2
    else:
        id += (x_cord - 1) / 2

    return int(id)


def linear_interpolate(a: float, b: float, t: float) -> float:
    return a + t * (b - a)



def flush_input():
    termios.tcflush(sys.stdin, termios.TCIFLUSH)
