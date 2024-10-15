import cv2 as cv
import numpy as np
import math
import traceback

from computer_vision.board_recognition.game_board_recognition import Board
from computer_vision.checkers_recognition.checkers_recognition import Checkers, Color

from resource import *

def list_ports():

	# Test the ports and returns a tuple with the available ports and the ones that are working.

	is_working = True
	dev_port = 0
	working_ports = []
	available_ports = []
	while dev_port < 10: #is_working:
		camera = cv.VideoCapture(dev_port)
		if not camera.isOpened():
			# is_working = False
			print("Port %s is not working." %dev_port)
			dev_port += 1
		else:
			is_reading, img = camera.read()
			w = camera.get(3)
			h = camera.get(4)
			if is_reading:
				print("Port %s is working and reads images (%s x %s)" %(dev_port,h,w))
				working_ports.append(dev_port)
			else:
				print("Port %s for camera ( %s x %s) is present but does not reads." %(dev_port,h,w))
				available_ports.append(dev_port)
			dev_port +=1
	return available_ports,working_ports

def empt_fun(a):
    pass


def get_pts_dist(pt1 = [0,0], pt2 = [0,0]):
    dx = pt1[0] - pt2[0]
    dy = pt1[1] - pt2[1]

    dx = float(dx*dx)
    dy = float(dy*dy)

    return math.sqrt(dx+dy)


def get_avg_pos(pts = [[0,0],[0,0]]):
    x_avg, y_avg = 0, 0

    for pt in pts:
        x_avg += pt[0]
        y_avg += pt[1]

    x_avg = int( float(x_avg) / float(len(pts)) )
    y_avg = int( float(y_avg) / float(len(pts)) )

    return [x_avg, y_avg]


def get_board_mask(pts, img_shape, margin = 10):
    center = get_avg_pos(pts)

    for pt in pts:
        dst = get_pts_dist(pt, center)
        pt[0] = center[0] + int(float(pt[0]-center[0])/dst*(dst+margin))
        pt[1] = center[1] + int(float(pt[1]-center[1])/dst*(dst+margin))
    
    pts = np.array(pts)
    mask = np.zeros(img_shape[:2],dtype="uint8")
    cv.fillConvexPoly(mask, pts, 1)
    return mask


def rotate_square_2D_matrix_right(matrix):
    new_matrix = []

    for _ in matrix[0]:
        new_matrix.append([])

    for x in range(0,len(matrix),1):
        for y in range(0,len(matrix[x]),1):
            new_matrix[y].append(matrix[x][len(matrix[x])-y-1])

    return new_matrix



class Game:

    @classmethod
    def build_game_state(cls, checkers, is_00_white=True):

        game_state = [
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0]
        ]

        for c in checkers:
            if c.color == Color.RED:
                game_state[c.pos[0]][c.pos[1]] = 1
            else:
                game_state[c.pos[0]][c.pos[1]] = -1

        if not is_00_white:
            game_state = rotate_square_2D_matrix_right(game_state)

        return game_state


    def __init__(self, handle_capture = True, lack_of_trust_level = 5):

        # Convention: 
        # game state is 2d matrix -> list of columns
        # 1 represents red, -1 represents green
        # the reds are on the upper side
        # the game_state[0][0] is the upper left field
        # the game_state[7][7] is the bottom right field
        # the upper side is y = 0
        # the bottom side is y = 7

        if handle_capture:
            
            # Looking for available cameras
            available_ports, working_ports = list_ports()

            print('\nPlease select camera port by index')
            for i,p in enumerate(working_ports):
                print(f'[{i}]: {p}')

            port_idx = int(input())

            port = working_ports[port_idx]#[0]
            #port = port_idx
            
            self.cap = cv.VideoCapture()
            self.cap.open(port)
            self.cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter.fourcc(	'M', 'J', 'P', 'G'))
            self.cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920)
            self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)

            self.bgrs = []
            self.calibration_frame = None
            self.red_checker_bgr, self.blue_checker_bgr, self.dark_field_bgr, self.light_field_bgr = self.calibrate_colors()

            cv.namedWindow("Parameters - Board")
            cv.resizeWindow("Parameters - Board", 640, 340)
            cv.createTrackbar("Threshold1", "Parameters - Board", 140, 255, empt_fun)
            cv.createTrackbar("Threshold2", "Parameters - Board", 255, 255, empt_fun)
            cv.createTrackbar("Min_area", "Parameters - Board", 150, 600, empt_fun)
            cv.createTrackbar("Area_margin", "Parameters - Board", 500, 700, empt_fun)
            cv.createTrackbar("Kernel_size", "Parameters - Board", 5, 10, empt_fun)
            cv.createTrackbar("Approx_peri", "Parameters - Board", 3, 50, empt_fun)
            cv.createTrackbar("Px_dist", "Parameters - Board", 15, 100, empt_fun)
            cv.createTrackbar("Color_dist_threshold", "Parameters - Board", 80, 200, empt_fun)

            self.handle_capture = True

        else:
            self.handle_capture = False
        
        self.game_state = [
            [0,1,0,0,0,-1,0,-1],
            [1,0,1,0,0,0,-1,0],
            [0,1,0,0,0,-1,0,-1],
            [1,0,1,0,0,0,-1,0],
            [0,1,0,0,0,-1,0,-1],
            [1,0,1,0,0,0,-1,0],
            [0,1,0,0,0,-1,0,-1],
            [1,0,1,0,0,0,-1,0]
        ]

        self.game_state_log = [self.game_state]
        self.lack_of_trust_level = lack_of_trust_level


    def calibration_mouse_listener(self,event,x,y,flags,param):

        if event == cv.EVENT_LBUTTONUP:

            self.bgrs.append(self.calibration_frame[y][x])


    def calibrate_colors(self):

        self.bgrs = []
        cnt = 0
        texts = [
            "SELECT ORANGE CHECKER",
            "SELECT BLUE CHECKER",
            "SELECT DARK FIELD",
            "SELECT LIGHT FIELD"
        ]

        tmp = np.zeros((1,1,3), dtype = np.uint8)
        cv.imshow("Calibration", tmp)

        cv.setMouseCallback("Calibration", self.calibration_mouse_listener)

        while len(self.bgrs) < 4:

            success, img = self.cap.read()

            cv.putText(img, texts[cnt], (int(img.shape[0]/10), int(img.shape[1]/2)), cv.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 3, cv.LINE_AA)

            img = cv.resize(img, (0,0), fx=0.8, fy=0.8)
            cv.imshow("Calibration", img)
            self.calibration_frame = img

            cnt = len(self.bgrs)

            if cv.waitKey(30) == ord('q'): #& 0xFF == ord('q'):
                break

        cv.destroyAllWindows()

        return self.bgrs


    def present_visually(self):

        img = np.zeros((500,500,3), np.uint8) #create black empty plane
        img[:,:] = (240,240,240) #setting background

        is_dark = False
        for x in range(0,8,1):  # drawing fields
            for y in range(0,8,1):

                if is_dark:
                    cv.rectangle(img, (x*50+50,y*50+50),(x*50+100,y*50+100),(0,25,80),-1)
                else:
                    cv.rectangle(img, (x*50+50,y*50+50),(x*50+100,y*50+100),(180,225,255),-1)
                
                is_dark = not is_dark
            is_dark = not is_dark
        
        for i in range(0,9,1):
            cv.line(img, [50 + i*50, 50], [50 + i*50, 450], (0,0,0), 3) #drawing vertical lines
            cv.line(img, [50, 50 + i*50], [450, 50 + i*50], (0,0,0), 3) #drawing horizontal lines

        for x,_ in enumerate(self.game_state): #drawing checkers
            for y,_ in enumerate(self.game_state[x]):
                if self.game_state[x][y] == 1:
                    cv.circle(img, [x*50+75,y*50+75],20,(50,85,220),-1)
                if self.game_state[x][y] == -1:
                    cv.circle(img, [x*50+75,y*50+75],20,(205,105,60),-1)

        return img

    
    def handle_next_frame(self, frame):

        img_res = frame.copy()

        t1 = cv.getTrackbarPos("Threshold1", "Parameters - Board")
        t2 = cv.getTrackbarPos("Threshold2", "Parameters - Board")
        kernel_size = cv.getTrackbarPos("Kernel_size", "Parameters - Board")
        min_area = cv.getTrackbarPos("Min_area", "Parameters - Board")
        area_margin = cv.getTrackbarPos("Area_margin", "Parameters - Board")
        approx_peri_fraction = float(cv.getTrackbarPos("Approx_peri", "Parameters - Board")) / 100.0
        px_dist_to_join = float(cv.getTrackbarPos("Px_dist", "Parameters - Board"))
        color_dist_thresh = cv.getTrackbarPos("Color_dist_threshold", "Parameters - Board")

        try:
            board = Board.detect_board(img_res, t1 =t1, t2= t2, kernel = np.ones((kernel_size, kernel_size)), min_area = min_area, area_margin = area_margin, approx_peri_fraction = approx_peri_fraction, px_dist_to_join = px_dist_to_join)
        
            Checkers.detect_checkers(board, frame, self.red_checker_bgr, self.blue_checker_bgr, color_dist_thresh)

            has_changed = self.challange_game_state_change(Game.build_game_state(Checkers.checkers, is_00_white = board.is_00_white(
                dark_field_bgr = self.dark_field_bgr, 
                light_field_bgr = self.light_field_bgr, 
                red_bgr = self.red_checker_bgr, 
                green_bgr = self.blue_checker_bgr, 
                color_dist_thresh = color_dist_thresh
            )))

        except Exception:
            #print("\n=-=-=--=-=-=-=-=-=-=-=-=-=-= Couldn't map board =-=-=--=-=-=-=-=-=-=-=-=-=-=\n")
            img_res = cv.resize(img_res, (0,0), fx=0.8, fy=0.8)
            cv.imshow("RESULT", img_res)
            raise Exception("Couldn't map board")

        img_res = cv.resize(img_res, (0,0), fx=0.8, fy=0.8)
        cv.imshow("RESULT", img_res)
        cv.imshow("GAME STATE", self.present_visually())
        cv.waitKey(1)
        return has_changed


    def capture_next_frame(self):
        if not self.handle_capture:
            success = False
        else:
            success, img = self.cap.read()

        if success:
            return img

        raise Exception("Failure during capturing frame or capture mode not selected")


    def challange_game_state_change(self, game_state):

        if game_state is None:
            return False

        for l in self.game_state_log:
            if l != game_state:
                self.game_state_log = [game_state]
                #print("============NOT THE SAME=============")
                #print(l)
                #print(game_state)
                return False

        if len(self.game_state_log) + 1 >= self.lack_of_trust_level:
            self.game_state = game_state
            self.game_state_log = [game_state]
            #print("============UPDATED =============")
            return True

        self.game_state_log.append(game_state)
        #print("============SAME but need more =============")
        return False


    def get_fresh_game_state(self):

        new_frame = self.capture_next_frame()

        has_state_possibly_change = self.handle_next_frame(new_frame)

        return has_state_possibly_change, [i.copy() for i in self.game_state]


def main_old():

    game = Game(handle_capture = False)

    cap = cv.VideoCapture()
    cap.open('/dev/v4l/by-id/usb-Xiongmai_web_camera_12345678-video-index0')
    cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter.fourcc(	'M', 'J', 'P', 'G'))
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)
    #v4l2-ctl -d 2 --set-fmt-video pixelformat=0,width=1920,height=1080
    #ffmpeg -f v4l2 -input_format mjpg -i /dev/video2 -c:v copy output.mkv

    while True:

        success, img = cap.read()
        img_res = img.copy()
        img_checker_masked = img.copy()

        t1 = cv.getTrackbarPos("Threshold1", "Parameters - Board")
        t2 = cv.getTrackbarPos("Threshold2", "Parameters - Board")
        kernel_size = cv.getTrackbarPos("Kernel_size", "Parameters - Board")
        min_area = cv.getTrackbarPos("Min_area", "Parameters - Board")
        area_margin = cv.getTrackbarPos("Area_margin", "Parameters - Board")
        approx_peri_fraction = float(cv.getTrackbarPos("Approx_peri", "Parameters - Board")) / 100.0
        px_dist_to_join = float(cv.getTrackbarPos("Px_dist", "Parameters - Board"))

        dp = float(cv.getTrackbarPos("DP", "Parameters - Checkers"))/100.0
        #minDist = cv.getTrackbarPos("MinDist", "Parameters - Checkers")
        param1 = cv.getTrackbarPos("Param1", "Parameters - Checkers")
        param2 = cv.getTrackbarPos("Param2", "Parameters - Checkers")
        #minRadius = cv.getTrackbarPos("MinRadius", "Parameters - Checkers")
        #maxRadius = cv.getTrackbarPos("MaxRadius", "Parameters - Checkers")
        t1c = cv.getTrackbarPos("Threshold1", "Parameters - Checkers")
        t2c = cv.getTrackbarPos("Threshold2", "Parameters - Checkers")
        kernel_c = cv.getTrackbarPos("Kernel_size", "Parameters - Checkers")


        try:
            board = Board.detect_board(img_res, t1 =t1, t2= t2, kernel = np.ones((kernel_size, kernel_size)), min_area = min_area, area_margin = area_margin, approx_peri_fraction = approx_peri_fraction, px_dist_to_join = px_dist_to_join)
        
            Checkers.detect_checkers(board, img)

            game.challange_game_state_change(Game.build_game_state(Checkers.checkers, is_00_white = board.is_00_white(
                dark_field_bgr = self.dark_field_bgr, 
                light_field_bgr = self.light_field_bgr, 
                red_bgr = self.red_checker_bgr, 
                green_bgr = self.blue_checker_bgr, 
                color_dist_thresh = color_dist_thresh
            )))
        except Exception:
            print(traceback.format_exc())

        img_res = cv.resize(img_res, (0,0), fx=0.8, fy=0.8)
        cv.imshow("RESULT", img_res)

        cv.imshow("GAME STATE", game.present_visually())

        if cv.waitKey(1) == ord('q'): #& 0xFF == ord('q'):
            break


def main():
    game = Game()

    while True:

        game.get_fresh_game_state()

        if cv.waitKey(1) == ord('q'): #& 0xFF == ord('q'):
            break

def setup_param_controller():
    cv.namedWindow("Parameters - Board")
    cv.resizeWindow("Parameters - Board", 640, 340)
    cv.createTrackbar("Threshold1", "Parameters - Board", 140, 255, empt_fun)
    cv.createTrackbar("Threshold2", "Parameters - Board", 255, 255, empt_fun)
    cv.createTrackbar("Min_area", "Parameters - Board", 150, 600, empt_fun)
    cv.createTrackbar("Area_margin", "Parameters - Board", 500, 700, empt_fun)
    cv.createTrackbar("Kernel_size", "Parameters - Board", 2, 10, empt_fun)
    cv.createTrackbar("Approx_peri", "Parameters - Board", 3, 50, empt_fun)
    cv.createTrackbar("Px_dist", "Parameters - Board", 15, 100, empt_fun)

    cv.namedWindow("Parameters - Checkers")
    cv.resizeWindow("Parameters - Checkers", 640, 340)
    cv.createTrackbar("DP", "Parameters - Checkers", 20, 400, empt_fun)
    cv.createTrackbar("MinDist", "Parameters - Checkers", 10, 100, empt_fun)
    cv.createTrackbar("Param1", "Parameters - Checkers", 65, 400, empt_fun)
    cv.createTrackbar("Param2", "Parameters - Checkers", 15, 200, empt_fun)
    cv.createTrackbar("MinRadius", "Parameters - Checkers", 2, 100, empt_fun)
    cv.createTrackbar("MaxRadius", "Parameters - Checkers", 8, 100, empt_fun)
    #cv.createTrackbar("Threshold1", "Parameters - Checkers", 24, 255, empt_fun)
    #cv.createTrackbar("Threshold2", "Parameters - Checkers", 73, 255, empt_fun)
    cv.createTrackbar("Threshold1", "Parameters - Checkers", 140, 255, empt_fun)
    cv.createTrackbar("Threshold2", "Parameters - Checkers", 80, 255, empt_fun)
    cv.createTrackbar("Kernel_size", "Parameters - Checkers", 3, 10, empt_fun)



if __name__ == '__main__':

    main()
