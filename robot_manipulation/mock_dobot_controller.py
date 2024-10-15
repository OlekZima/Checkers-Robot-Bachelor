# all libs are for conda env test

from serial.tools import list_ports
import pydobot
import numpy as np
import cv2 as cv


class DobotController():

    def __init__(self, color):
        print("\nDobot controller init and calibration completed\n")

    def perform_move(self, move = [1,1], crown = False, height = 10):

        print(f'''
====================
DOBOT CONTROLLER INSTRUCTION:
    move = {move}
    crown = {crown}
    height = {height}

PERFORM MOVE AND PRESS ENTER
====================
        ''')

        input()