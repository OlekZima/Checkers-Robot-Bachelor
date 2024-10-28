import cv2 as cv
import numpy as np
import math
import traceback

from .rectangle_recognition  import get_game_tiles_contours

def empt_fun(a):
    pass


def get_avg_pos(pts = [[0,0],[0,0]]):
    x_avg, y_avg = 0, 0

    for pt in pts:
        x_avg += pt[0]
        y_avg += pt[1]

    x_avg = int( float(x_avg) / float(len(pts)) )
    y_avg = int( float(y_avg) / float(len(pts)) )

    return [x_avg, y_avg]


def get_triangle_area(p1=[0,0],p2=[0,0],p3=[0,0]):

    #Area = (1/2) |x1(y2 − y3) + x2(y3 − y1) + x3(y1 − y2)|

    area = abs(
        p1[0] * (p2[1] - p3[1])+
        p2[0] * (p3[1] - p1[1])+
        p3[0] * (p1[1] - p2[1])
    )

    area = float(area)/2.0

    return area


def get_mirrored_2d_matrix_y_axis(matrix):

    new_matrix = []
    col_num = len(matrix)

    for c in range(0,col_num,1):
        new_matrix.append(matrix[col_num-1-c])

    return new_matrix


def get_avg_color(img):
    b_val = 0
    g_val = 0
    r_val = 0

    for i in img:
        for j in i:
            b_val += j[0]
            g_val += j[1]
            r_val += j[2]

    n = img.shape[0]*img.shape[1]
    b_val /= n
    g_val /= n
    r_val /= n

    return [b_val, g_val, r_val]


def distance_from_color(bgr_sample, bgr_target):
    dist = (
        (bgr_sample[0]-bgr_target[0])**2 + 
        (bgr_sample[1]-bgr_target[1])**2 + 
        (bgr_sample[2]-bgr_target[2])**2
    )
    dist = math.sqrt(dist)
    return dist



class Board:

    @classmethod
    def detect_board(cls, img_src, t1 = 140, t2 = 255, kernel = np.ones((2,2)), min_area = 150, area_margin = 20, approx_peri_fraction = 0.03, px_dist_to_join = 10.0):
        
        contours = get_game_tiles_contours(img_src, t1 =t1, t2= t2, kernel = kernel, min_area = min_area, area_margin = area_margin, approx_peri_fraction = approx_peri_fraction, px_dist_to_join = px_dist_to_join)

        BoardTile.create_tiles(img_src, contours)

        try:
            return Board(img_src, BoardTile.tiles)

        except Exception:
            raise Exception("Error occured while trying to detect board")


    def __init__(self, img, board_tiles = []):

        self.frame = img

        self.tiles = board_tiles

        self.points = [] #shape == (9,9,2)
        for i in range(0,9,1):
            self.points.append([])
            for j in range(0,9,1):
                self.points[i].append(None)

        self.vertexes = [None, None, None, None]

        # STEP 0 - choosing a starting tile that has a neighbour in direction0
        # 
        # Also determinig what direction0 is in radians

        start_tile = None

        for tile in self.tiles:
            if tile.n_of_neighbours == 4:
                start_tile = tile
                break
        
        if start_tile is None:
            #print('======== jestem w Board __init__ -> niue znalazłem początkowego pola =======')
            raise Exception("Couldn't find starting tile") #TODO -> custom exceptions
        else:
            
            # print(board.start_tile.vertexes)
            cv.circle(self.frame, start_tile.center, 3, (0, 0, 255), -1) #just for testing purposes
            #print(start_tile.vertexes)
        
        # STEP 1 - finding indexes of start_tile by recursive function of BoardTile (flood_fill like)

        try:
            Board.set_index_of_start_tile(start_tile)
            #cv.putText(self.frame, f'{start_tile.x_idx},{start_tile.y_idx}', start_tile.center, cv.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1, cv.LINE_AA)

        except Exception:
            #print('======== jestem w Board __init__ -> coś się wykrzaczyło przy szykaniu indexów start tile=======')
            raise Exception("Insufficient data!!! Not enough board is recognized")

        # STEP 2 - indexing all tiles by second recursive function
        
        Board.set_all_tiles_indexes(start_tile)

        # STEP 3 - assigning Board coordinates using indexes

        dir_0 = start_tile.get_dir_0_radians()
        self.set_all_known_board_points(dir_0)

        #print(f'''
        #[0][0] = {[v * 2 for v in self.points[0][0]]}
        #[0][8] = {[v * 2 for v in self.points[0][8]]}
        #[8][8] = {[v * 2 for v in self.points[8][8]]}
        #[8][0] = {[v * 2 for v in self.points[8][0]]}
        #''')


        # STEP 4 - calculating final board dimensions - vertexes

        self.calculate_vertexes()

        cv.circle(self.frame, self.vertexes[0], 3, (0, 255, 0), -1)
        cv.circle(self.frame, self.vertexes[1], 3, (0, 255, 0), -1)
        cv.circle(self.frame, self.vertexes[2], 3, (0, 255, 0), -1)
        cv.circle(self.frame, self.vertexes[3], 3, (0, 255, 0), -1)
        #cv.line(self.frame, self.vertexes[0], self.vertexes[1], (0, 255, 0), 2)
        #cv.line(self.frame, self.vertexes[1], self.vertexes[2], (0, 255, 0), 2)
        #cv.line(self.frame, self.vertexes[2], self.vertexes[3], (0, 255, 0), 2)
        #cv.line(self.frame, self.vertexes[3], self.vertexes[0], (0, 255, 0), 2)


        # STEP 5 - interpolating all points on board

        self.interpolate_borders() # first I need to know all border points

        self.interpolate_inner_points() # then I interpolate all inner points


        # STEP 6 - mirroring self.points for future use

        self.points = get_mirrored_2d_matrix_y_axis(self.points)
        
        
        # STEP 7 - drawing board for testing purposes

        for i in range(0,9,1):
            for j in range(0,9,1):
                if i != 8:
                    if self.points[i][j] is not None and self.points[i+1][j] is not None:
                        cv.line(self.frame,self.points[i][j] ,self.points[i+1][j] , (0, 255, 0), 1)
                if j != 8:
                    if self.points[i][j] is not None and self.points[i][j+1] is not None:
                        cv.line(self.frame,self.points[i][j] ,self.points[i][j+1] , (0, 255, 0), 1)


    @classmethod
    def set_index_of_start_tile(cls, start_tile):
        
        # calculating directions
        dir_0 = start_tile.get_dir_0_radians()

        dir_01 = dir_0 + math.pi / 4.0
        if dir_01 >= math.pi * 2.0:
            dir_01 -= math.pi * 2.0
        
        dir_1 = dir_0 + math.pi / 2.0
        if dir_1 >= math.pi * 2.0:
            dir_1 -= math.pi * 2.0

        dir_12 = dir_1 + math.pi / 4.0
        if dir_12 >= math.pi * 2.0:
            dir_12 -= math.pi * 2.0

        dir_2 = dir_1 + math.pi / 2.0
        if dir_2 >= math.pi * 2.0:
            dir_2 -= math.pi * 2.0

        dir_23 = dir_2 + math.pi / 4.0
        if dir_23 >= math.pi * 2.0:
            dir_23 -= math.pi * 2.0

        dir_3 = dir_2 + math.pi / 2.0
        if dir_3 >= math.pi * 2.0:
            dir_3 -= math.pi * 2.0

        dir_30 = dir_3 + math.pi / 4.0
        if dir_30 >= math.pi * 2.0:
            dir_30 -= math.pi * 2.0

        #print(f'''================================================================================================
        #\ndir_0 = {dir_0}, dir_1 = {dir_1}, dir_2 = {dir_2}, dir_3 = {dir_3}
        #\ndir_01 = {dir_01}, dir_12 = {dir_12}, dir_23 = {dir_23}, dir_30 = {dir_30}
        #\nstart_tile.center = {start_tile.center}
        #\nn01.center = {start_tile.n01.center}
        #\ndir_to_n01 = {start_tile.get_dir_2_point_rad(start_tile.n01.center)}
        #\nn12.center = {start_tile.n12.center}
        #\ndir_to_n12 = {start_tile.get_dir_2_point_rad(start_tile.n12.center)}
        #\nn23.center = {start_tile.n23.center}
        #\ndir_to_n23 = {start_tile.get_dir_2_point_rad(start_tile.n23.center)}
        #\nn30.center = {start_tile.n30.center}
        #\ndir_to_n30 = {start_tile.get_dir_2_point_rad(start_tile.n30.center)}''')

        # getting x index and checking if we have sufficient data to settle it
        dir_1_neighbour = start_tile.get_neighbour_in_rad_range(dir_01, dir_12)
        if dir_1_neighbour is None:
            #print("Nie mam somsiada na dir_1 :(")
            dir_1_steps = 0
        else:
            dir_1_steps = start_tile.get_num_of_steps_in_dir_rad(dir_1, 1)
            #print(f"Mam somsiada na dir_1!!!, dir_1 = {dir_1_steps} kroków")
        
        dir_3_neighbour = start_tile.get_neighbour_in_rad_range(dir_23, dir_30)
        if dir_3_neighbour is None:
            #print("Nie mam somsiada na dir_3 :(")
            dir_3_steps = 0
        else:
            dir_3_steps = start_tile.get_num_of_steps_in_dir_rad(dir_3, 3)
            #print(f"Mam somsiada na dir_3!!!, dir_3 = {dir_3_steps} kroków")

        if dir_1_steps + dir_3_steps != 7:
            #print(f'======= jestem w Board set_index ... -> coś się wykrzaczyło przy x\ndir_1_steps = {dir_1_steps}\ndir_3_steps = {dir_3_steps}')
            raise Exception("Insufficient data!!! Not enough board is recognized")

        start_tile.assign_x_idx(dir_3_steps)

        # getting y index and checking if we have sufficient data to settle it
        dir_2_neighbour = start_tile.get_neighbour_in_rad_range(dir_12, dir_23)
        if dir_2_neighbour is None:
            #print("Nie mam somsiada na dir_2 :(")
            dir_2_steps = 0
        else:
            dir_2_steps = start_tile.get_num_of_steps_in_dir_rad(dir_2, 2)
            #print(f"Mam somsiada na dir_2!!!, dir_2 = {dir_2_steps} kroków")
        
        dir_0_neighbour = start_tile.get_neighbour_in_rad_range(dir_30, dir_01)
        if dir_0_neighbour is None:
            #print("Nie mam somsiada na dir_0 :(")
            dir_0_steps = 0
        else:
            dir_0_steps = start_tile.get_num_of_steps_in_dir_rad(dir_0, 0)
            #print(f"Mam somsiada na dir_0!!!, dir_0 = {dir_0_steps} kroków")

        if dir_2_steps + dir_0_steps != 7:
            #print('======= jestem w Board set_index ... -> coś się wykrzaczyło przy y\ndir_2_steps = {dir_2_steps}\ndir_0_steps = {dir_0_steps}')
            raise Exception("Insufficient data!!! Not enough board is recognized")

        start_tile.assign_y_idx(dir_0_steps)
        #print(f'Index start_tile to x = {dir_3_steps} y = {dir_0_steps}')


    @classmethod
    def set_all_tiles_indexes(cls, start_tile):
        dir_0 = start_tile.get_dir_0_radians()

        start_tile.index_neighbours(dir_0)


    def set_all_known_board_points(self, dir_0):
        
        dir_1 = dir_0 + math.pi / 2.0
        if dir_1 >= math.pi * 2.0:
            dir_1 -= math.pi * 2.0

        dir_2 = dir_1 + math.pi / 2.0
        if dir_2 >= math.pi * 2.0:
            dir_2 -= math.pi * 2.0

        dir_3 = dir_2 + math.pi / 2.0
        if dir_3 >= math.pi * 2.0:
            dir_3 -= math.pi * 2.0

        
        for tile in self.tiles:
            if tile.x_idx is None or tile.y_idx is None:
                continue
            if self.points[tile.x_idx][tile.y_idx] is None:
                self.points[tile.x_idx][tile.y_idx] = tile.get_vertex_in_rad_range(dir_3,dir_0)

            if self.points[tile.x_idx+1][tile.y_idx] is None:
                self.points[tile.x_idx+1][tile.y_idx] = tile.get_vertex_in_rad_range(dir_0, dir_1)

            if self.points[tile.x_idx+1][tile.y_idx+1] is None:
                self.points[tile.x_idx+1][tile.y_idx+1] = tile.get_vertex_in_rad_range(dir_1,dir_2)

            if self.points[tile.x_idx][tile.y_idx+1] is None:
                self.points[tile.x_idx][tile.y_idx+1] = tile.get_vertex_in_rad_range(dir_2,dir_3)


    @classmethod
    def extrapolate_last_point(cls, pts = [[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0]]):

        # This function will take one side of a Board as list of points
        # Then check what are 2 not None values the most appart from itself
        # Finally extrapolating the last item on this list accordingly
        
        min_idx = 8
        max_idx = 0
        for i,p in enumerate(pts):
            if p is not None:
                if i < min_idx:
                    min_idx = i
                if i > max_idx:
                    max_idx = i
        
        vector_init_len = max_idx - min_idx
        vector_final_len = 8 - min_idx

        vector = [pts[max_idx][0]-pts[min_idx][0],pts[max_idx][1]-pts[min_idx][1]]
        vector = [int(float(v) / float(vector_init_len) * vector_final_len) for v in vector]

        res = [pts[min_idx][0]+vector[0],pts[min_idx][1]+vector[1]]

        return res


    def calculate_vertexes(self):

        if self.points[0][0] is not None:
            self.vertexes[0] = self.points[0][0]

        if self.points[8][0] is not None:
            self.vertexes[1] = self.points[8][0]

        if self.points[8][8] is not None:
            self.vertexes[2] = self.points[8][8]

        if self.points[0][8] is not None:
            self.vertexes[3] = self.points[0][8]

        
        if self.vertexes[0] is None:
            P_01 = [v[0] for v in self.points]
            P_10 = P_01[::-1]
            pred1 = Board.extrapolate_last_point(pts=P_10)

            P_03 = self.points[0]
            P_30 = P_03[::-1]
            pred2 = Board.extrapolate_last_point(pts=P_30)

            res = get_avg_pos([pred1, pred2])
            self.vertexes[0] = res
            self.points[0][0] = res

        if self.vertexes[1] is None:
            P_01 = [v[0] for v in self.points]
            pred1 = Board.extrapolate_last_point(pts=P_01)

            P_12 = self.points[8]
            P_21 = P_12[::-1]
            pred2 = Board.extrapolate_last_point(pts=P_21)

            res = get_avg_pos([pred1, pred2])
            self.vertexes[1] = res
            self.points[8][0] = res
        
        if self.vertexes[2] is None:
            P_12 = self.points[8]
            pred1 = Board.extrapolate_last_point(pts=P_12)

            P_32 = [v[8] for v in self.points]
            pred2 = Board.extrapolate_last_point(pts=P_32)

            res = get_avg_pos([pred1, pred2])
            self.vertexes[2] = res
            self.points[8][8] = res
        
        if self.vertexes[3] is None:
            P_32 = [v[8] for v in self.points]
            P_23 = P_32[::-1]
            pred1 = Board.extrapolate_last_point(pts=P_23)

            P_03 = self.points[0]
            pred2 = Board.extrapolate_last_point(pts=P_03)

            res = get_avg_pos([pred1, pred2])
            self.vertexes[3] = res
            self.points[0][8] = res


    def interpolate_borders(self):
        
        P_01 = [v[0] for v in self.points]
        P_12 = self.points[8]
        P_32 = [v[8] for v in self.points]
        P_03 = self.points[0]

        #Border 01
        for i in range(1,len(P_01)-1, 1):
            if P_01[i] is None:
                pts_to_avg = []
                for j in range(i+1, len(P_01),1):
                    pts_to_avg.append(P_01[i-1])
                    if P_01[j] is not None:
                        pts_to_avg.append(P_01[j])
                        break
        
                extrapolation_pts = self.points[i][::-1]
                extrapolation_val = Board.extrapolate_last_point(pts = extrapolation_pts)

                pts_to_avg = [get_avg_pos(pts_to_avg),extrapolation_val]

                self.points[i][0] = get_avg_pos(pts_to_avg)
                P_01[i] = self.points[i][0]

        #Border 12
        for i in range(1,len(P_12)-1, 1):
            if P_12[i] is None:
                pts_to_avg = []
                for j in range(i+1, len(P_12),1):
                    pts_to_avg.append(P_12[i-1])
                    if P_12[j] is not None:
                        pts_to_avg.append(P_12[j])
                        break
        
                extrapolation_pts = [l[i] for l in self.points]
                extrapolation_val = Board.extrapolate_last_point(pts = extrapolation_pts)

                pts_to_avg = [get_avg_pos(pts_to_avg),extrapolation_val]

                self.points[8][i] = get_avg_pos(pts_to_avg)
                P_12[i] = self.points[8][i]

        #Border 23
        for i in range(1,len(P_32)-1, 1):
            if P_32[i] is None:
                pts_to_avg = []
                for j in range(i+1, len(P_32),1):
                    pts_to_avg.append(P_32[i-1])
                    if P_32[j] is not None:
                        pts_to_avg.append(P_32[j])
                        break
        
                extrapolation_pts = self.points[i]
                extrapolation_val = Board.extrapolate_last_point(pts = extrapolation_pts)

                pts_to_avg = [get_avg_pos(pts_to_avg),extrapolation_val]

                self.points[i][8] = get_avg_pos(pts_to_avg)
                P_32[i] = self.points[i][8]

        #Border 30
        for i in range(1,len(P_03)-1, 1):
            if P_03[i] is None:
                pts_to_avg = []
                for j in range(i+1, len(P_03),1):
                    pts_to_avg.append(P_03[i-1])
                    if P_03[j] is not None:
                        pts_to_avg.append(P_03[j])
                        break
        
                extrapolation_pts = [l[i] for l in self.points][::-1]
                extrapolation_val = Board.extrapolate_last_point(pts = extrapolation_pts)

                pts_to_avg = [get_avg_pos(pts_to_avg),extrapolation_val]

                self.points[0][i] = get_avg_pos(pts_to_avg)
                P_03[i] = self.points[0][i]


    def interpolate_inner_points(self):

        for i in range(1, len(self.points)-1, 1):
            for j in range(1, len(self.points[i])-1, 1):
                if self.points[i][j] is None:
                    pts_to_avg_same_i = []
                    pts_to_avg_same_j = []

                    for k in range(j+1, len(self.points[i]), 1):
                        pts_to_avg_same_i.append(self.points[i][j-1])
                        if self.points[i][k] is not None:
                            pts_to_avg_same_i.append(self.points[i][k])
                            break

                    for k in range(i+1, len(self.points), 1):
                        pts_to_avg_same_j.append(self.points[i-1][j])
                        if self.points[k][j] is not None:
                            pts_to_avg_same_j.append(self.points[k][j])
                            break

                    self.points[i][j] = get_avg_pos([get_avg_pos(pts_to_avg_same_i),get_avg_pos(pts_to_avg_same_j)])


    def is_point_in_field(self,x,y,pt=[0,0]):
        #the idea is to check if field area == area of 4 triangles with pt vertex

        v1 = self.points[x][y]
        v2 = self.points[x+1][y]
        v3 = self.points[x+1][y+1]
        v4 = self.points[x][y+1]

        field_area = get_triangle_area(v1,v2,v3) + get_triangle_area(v3,v4,v1)

        calculated_area = (
            get_triangle_area(v1,pt,v2) +
            get_triangle_area(v2,pt,v3) +
            get_triangle_area(v3,pt,v4) +
            get_triangle_area(v4,pt,v1)
        )

        if field_area == calculated_area:
            return True
        return False


    def is_00_white(self, radius=4, dark_field_bgr = [0,0,0], light_field_bgr = [255,255,255], red_bgr = [0,0,255], green_bgr = [0,255,0], color_dist_thresh = 60):

        pt = get_avg_pos([
            self.points[0][0],
            self.points[0][1],
            self.points[1][1],
            self.points[1][0]
        ])

        sample = self.frame[(pt[1]-radius):(pt[1]+radius), (pt[0]-radius):(pt[0]+radius)]
        sample_avg_bgr = get_avg_color(sample)

        if (
            distance_from_color(sample_avg_bgr,dark_field_bgr) < distance_from_color(sample_avg_bgr,light_field_bgr)
            or distance_from_color(sample_avg_bgr, red_bgr) <= color_dist_thresh
            or distance_from_color(sample_avg_bgr, green_bgr) <= color_dist_thresh
        ):
            return False
        else:
            return True




class BoardTile:

    tiles = [] #storing all board tiles
    frame = None
    
    @classmethod
    def create_tiles(cls, img, contours):
        BoardTile.frame = img

        # contours.shape == ( -1, 4, 1, 2)

        # RESET - removing all previous tiles
        BoardTile.tiles = []

        
        # STEP 0 - creating tiles from all contours
        for cnt in contours:
            BoardTile.tiles.append(BoardTile(points=[cnt[0][0],cnt[1][0],cnt[2][0],cnt[3][0]]))

        BoardTile.tiles = np.array(BoardTile.tiles, dtype=BoardTile)
        
        # STEP 1 - only keepeing tiles that have at least 1 n_of_neighbours
        # - so that we only get our board tiles and not disconected false readings
        #
        # ALSO - connecting touching tiles with neighbour relation (see constructor)
        keep_cnt = np.zeros(BoardTile.tiles.shape, dtype=bool)


        for i, cnt1 in enumerate(BoardTile.tiles):
            for cntn in BoardTile.tiles[i+1:]:
                cnt1.assign_if_neighbour(cntn)
            
            if cnt1.n_of_neighbours >= 1: # Finally 1 works well
                keep_cnt[i] = True
                cv.circle(BoardTile.frame, cnt1.center, 3, (0, 0, 255), 1)
                #print(cnt1.n_of_neighbours)

        BoardTile.tiles = BoardTile.tiles[keep_cnt] # Keeping only tiles with at least 2 neighbours

        for tile in BoardTile.tiles:
            if tile.n01 is not None:
                if tile.n01 not in BoardTile.tiles:
                    tile.n01 = None
                    tile.n_of_neighbours -= 1
                else:
                    cv.line(BoardTile.frame, tile.center, tile.n01.center, (0,0,0), 1)
            if tile.n12 is not None:
                if tile.n12 not in BoardTile.tiles:
                    tile.n12 = None
                    tile.n_of_neighbours -= 1
                else:
                    pass#cv.line(BoardTile.frame, tile.center, tile.n12.center, (0,0,0), 1)
            if tile.n23 is not None:
                if tile.n23 not in BoardTile.tiles:
                    tile.n23 = None
                    tile.n_of_neighbours -= 1
                else:
                    pass#cv.line(BoardTile.frame, tile.center, tile.n23.center, (0,0,0), 1)
            if tile.n30 is not None:
                if tile.n30 not in BoardTile.tiles:
                    tile.n30 = None
                    tile.n_of_neighbours -= 1
                else:
                    cv.line(BoardTile.frame, tile.center, tile.n30.center, (0,0,0), 1)
            #cv.putText(BoardTile.frame, f'{tile.n_of_neighbours}', tile.center, cv.FONT_HERSHEY_SIMPLEX, 0.35, (0,255,0), 1, cv.LINE_AA)

    
    @classmethod
    def get_tiles_contours(cls):
        contours = np.ndarray((1,4,1,2), dtype=int)
        for t in BoardTile.tiles:
            contours = np.append(contours ,[[[t.vertexes[0]],[t.vertexes[1]],[t.vertexes[2]],[t.vertexes[3]]]] ,axis=0)
        return contours[1:]


    def __init__(self, points = [[0,0],[0,0],[0,0],[0,0]]):

        # theese will be used to see relation with other tiles 
        # and get the final position of the board
        self.vertexes = points
        self.center = get_avg_pos(points)
        #print (self.vertexes)
        
        # neighbouring tiles - theese will be assigned later to map the board
        #
        # neighbour n01 means that the neighbour share vertexes[0] and vertexes[1] points
        # with this tile
        self.n01 = None 
        self.n12 = None
        self.n23 = None
        self.n30 = None
        self.n_of_neighbours = 0 # will be updated when neighbours are assigned

        # ilustration showing direction naming convention and indexing algorithm:
        # https://drive.google.com/file/d/1BF7BsXUdXmlOtog8Z4uC_gXMGwE0EBmd/view?usp=sharing
        self.x_idx = None
        self.y_idx = None #Position on checkers board

        self.was_checked_in_dir_idx = [False, False, False, False]

    
    def assign_if_neighbour(self, poss_neighbour):

        for i,_ in enumerate(self.vertexes):
            for j,_ in enumerate(poss_neighbour.vertexes):
                if (self.vertexes[i] == poss_neighbour.vertexes[j]).all():
                    jp = 0 if j+1 == len(poss_neighbour.vertexes) else j+1
                    jm = len(poss_neighbour.vertexes) - 1 if j-1 == -1 else j-1
                    ip = 0 if i+1 == len(poss_neighbour.vertexes) else i+1
                    
                    if (self.vertexes[ip] == poss_neighbour.vertexes[jp]).all():
                        self.n01 = poss_neighbour if i == 0 else self.n01 # agrhhh awful
                        self.n12 = poss_neighbour if i == 1 else self.n12 
                        self.n23 = poss_neighbour if i == 2 else self.n23 
                        self.n30 = poss_neighbour if i == 3 else self.n30 
                        self.n_of_neighbours += 1
                        poss_neighbour.n01 = self if j == 0 else poss_neighbour.n01 # agrhhh awful
                        poss_neighbour.n12 = self if j == 1 else poss_neighbour.n12 
                        poss_neighbour.n23 = self if j == 2 else poss_neighbour.n23 
                        poss_neighbour.n30 = self if j == 3 else poss_neighbour.n30 
                        poss_neighbour.n_of_neighbours += 1
                        #print(f'{self.vertexes}\n{poss_neighbour.vertexes}')
                        return True

                    if (self.vertexes[ip] == poss_neighbour.vertexes[jm]).all():
                        self.n01 = poss_neighbour if i == 0 else self.n01 # agrhhh awful
                        self.n12 = poss_neighbour if i == 1 else self.n12 
                        self.n23 = poss_neighbour if i == 2 else self.n23 
                        self.n30 = poss_neighbour if i == 3 else self.n30 
                        self.n_of_neighbours += 1
                        poss_neighbour.n01 = self if jm == 0 else poss_neighbour.n01 # agrhhh awful
                        poss_neighbour.n12 = self if jm == 1 else poss_neighbour.n12 
                        poss_neighbour.n23 = self if jm == 2 else poss_neighbour.n23 
                        poss_neighbour.n30 = self if jm == 3 else poss_neighbour.n30 
                        poss_neighbour.n_of_neighbours += 1
                        #print(f'{self.vertexes}\n{poss_neighbour.vertexes}')
                        return True

        return False


    def assign_indexes(self, id_x, id_y):
        self.x_idx = id_x
        self.y_idx = id_y


    def assign_x_idx(self, x_idx):
        self.x_idx = x_idx


    def assign_y_idx(self, y_idx):
        self.y_idx = y_idx


    def get_dir_0_radians(self):
        if self.n01 is None:
            return None
        
        return self.get_dir_2_point_rad(self.n01.center)


    def get_dir_2_point_rad(self, point = [0,0]):
        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]

        # print(f'''Jestem sprawdzaczem kierunku do punktu
        # Ta kostka {self.center}, cel {point}
        # dx = {dx}, dy = {dy}''')

        dpi = 0

        if dx >= 0 and dy < 0:
            dpi = math.pi / 2.0
            tmp = dx
            dx = dy
            dy = tmp
        elif dx < 0 and dy < 0:
            dpi = math.pi
        elif dx < 0 and dy >= 0:
            dpi = 3 * math.pi / 2.0
            tmp = dx
            dx = dy
            dy = tmp

        dx = math.fabs(dx)
        dy = math.fabs(dy)

        if dy != 0:
            res = math.atan(float(dx)/float(dy))
            res += dpi

            # print(f'Obliczyłem: {res}')
            return res
        else:
            res = math.pi / 2.0
            res += dpi
            # print(f'Obliczyłem: {res}')

            return res


    def is_point_in_rad_range(self, rad_min, rad_max, point = [0,0]):
        dir_tmp = self.get_dir_2_point_rad(point)
        #print(f'''Sprawdzam, czy podany punkt jest w zakresie
        #Dostałem: rad_min = {rad_min}, rad_max = {rad_max}
        #Obliczyłem, że kierunek do punktu to {dir_tmp}''')
        if (rad_min <= rad_max and dir_tmp >= rad_min and dir_tmp <= rad_max) or (rad_min > rad_max and dir_tmp <= rad_max) or (rad_min > rad_max and dir_tmp >= rad_min):
            #print('Mój werdykt - TRUE')
            return True
        #print('Mój werdykt - FALSE')
        return False


    def get_neighbour_in_rad_range(self, rad_min, rad_max):
        if self.n01 is not None:
            if self.is_point_in_rad_range(rad_min, rad_max, self.n01.center):
                return self.n01
        if self.n12 is not None:
            if self.is_point_in_rad_range(rad_min, rad_max, self.n12.center):
                return self.n12
        if self.n23 is not None:
            if self.is_point_in_rad_range(rad_min, rad_max, self.n23.center):
                return self.n23
        if self.n30 is not None:
            if self.is_point_in_rad_range(rad_min, rad_max, self.n30.center):
                return self.n30
        
        return None


    def get_num_of_steps_in_dir_rad(self, dir_rad, dir_idx): #recursive function for indexing steps
        
        # if was checked already - returning 0
        if self.was_checked_in_dir_idx[dir_idx]:
            return 0
        
        # flagging self as checked already in dir_idx
        self.was_checked_in_dir_idx[dir_idx] = True
        
        # determining border between dirs
        dir_minus_min = dir_rad - math.pi * 3.0 / 4.0
        if dir_minus_min < 0:
            dir_minus_min += math.pi * 2.0

        dir_minus_max = dir_rad - math.pi / 4.0
        if dir_minus_max < 0:
            dir_minus_max += math.pi * 2.0

        dir_plus_min = dir_rad + math.pi / 4.0
        if dir_plus_min >= math.pi * 2.0:
            dir_plus_min -= math.pi * 2.0

        dir_plus_max = dir_rad + math.pi * 3.0 / 4.0
        if dir_plus_max >= math.pi * 2.0:
            dir_plus_max -= math.pi * 2.0

        # calling this func recursively for possibly 3 next tiles and gathering readings
        results = []

        same_dir = self.get_neighbour_in_rad_range(dir_minus_max, dir_plus_min)
        if same_dir is not None:
            results.append(same_dir.get_num_of_steps_in_dir_rad(dir_rad, dir_idx) + 1) # one more because it is in checked direction
        
        dir_minus = self.get_neighbour_in_rad_range(dir_minus_min, dir_minus_max)
        if dir_minus is not None:
            results.append(dir_minus.get_num_of_steps_in_dir_rad(dir_rad, dir_idx))

        dir_plus = self.get_neighbour_in_rad_range(dir_plus_min, dir_plus_max)
        if dir_plus is not None:
            results.append(dir_plus.get_num_of_steps_in_dir_rad(dir_rad, dir_idx))

        # retrieving data of max num of steps in dir
        max_num_of_steps = 0
        for res in results:
            if res > max_num_of_steps:
                max_num_of_steps = res

        # returning max value
        #if dir_idx == 1:
        #    cv.putText(BoardTile.frame, f'{max_num_of_steps}', self.center, cv.FONT_HERSHEY_SIMPLEX, 0.35, (0,255,0), 1, cv.LINE_AA)
        #if dir_idx == 3:
        #    cv.putText(BoardTile.frame, f'{max_num_of_steps}', (self.center[0], self.center[1]+5), cv.FONT_HERSHEY_SIMPLEX, 0.35, (0,0,255), 1, cv.LINE_AA)
        
        return max_num_of_steps


    def index_neighbours(self, dir_0):
        if self.x_idx is None or self.y_idx is None:
            return -1
        else:
            cv.putText(BoardTile.frame, f'{self.x_idx},{self.y_idx}', [self.center[0]-5, self.center[1]], cv.FONT_HERSHEY_SIMPLEX, 0.3, (0,255,0), 1, cv.LINE_AA)
        
        dir_01 = dir_0 + math.pi / 4.0
        if dir_01 >= math.pi * 2.0:
            dir_01 -= math.pi * 2.0
        
        dir_12 = dir_01 + math.pi / 2.0
        if dir_12 >= math.pi * 2.0:
            dir_12 -= math.pi * 2.0

        dir_23 = dir_12 + math.pi / 2.0
        if dir_23 >= math.pi * 2.0:
            dir_23 -= math.pi * 2.0

        dir_30 = dir_23 + math.pi / 2.0
        if dir_30 >= math.pi * 2.0:
            dir_30 -= math.pi * 2.0

        dir_0_n = self.get_neighbour_in_rad_range(dir_30, dir_01)
        dir_1_n = self.get_neighbour_in_rad_range(dir_01, dir_12)
        dir_2_n = self.get_neighbour_in_rad_range(dir_12,dir_23)
        dir_3_n = self.get_neighbour_in_rad_range(dir_23, dir_30)

        if dir_0_n is not None:
            if dir_0_n.x_idx is None or dir_0_n.y_idx is None:
                dir_0_n.assign_indexes(self.x_idx, self.y_idx-1)
                dir_0_n.index_neighbours(dir_0)

        if dir_1_n is not None:
            if dir_1_n.x_idx is None or dir_1_n.y_idx is None:
                dir_1_n.assign_indexes(self.x_idx+1, self.y_idx)
                dir_1_n.index_neighbours(dir_0)
                
        if dir_2_n is not None:
            if dir_2_n.x_idx is None or dir_2_n.y_idx is None:
                dir_2_n.assign_indexes(self.x_idx, self.y_idx+1)
                dir_2_n.index_neighbours(dir_0)
                
        if dir_3_n is not None:
            if dir_3_n.x_idx is None or dir_3_n.y_idx is None:
                dir_3_n.assign_indexes(self.x_idx-1, self.y_idx)
                dir_3_n.index_neighbours(dir_0)

        return 0


    def get_vertex_in_rad_range(self, rad_min, rad_max):
        for v in self.vertexes:
            if self.is_point_in_rad_range(rad_min, rad_max, v):
                return v
        return None




def main():
    
    while True:
        success, img = cap.read()
        img_res = img.copy()

        t1 = cv.getTrackbarPos("Threshold1", "Parameters")
        t2 = cv.getTrackbarPos("Threshold2", "Parameters")
        kernel_size = cv.getTrackbarPos("Kernel_size", "Parameters")
        min_area = cv.getTrackbarPos("Min_area", "Parameters")
        area_margin = cv.getTrackbarPos("Area_margin", "Parameters")
        approx_peri_fraction = float(cv.getTrackbarPos("Approx_peri", "Parameters")) / 100.0
        px_dist_to_join = float(cv.getTrackbarPos("Px_dist", "Parameters"))

        contours = get_game_tiles_contours(img, t1 =t1, t2= t2, kernel = np.ones((kernel_size, kernel_size)), min_area = min_area, area_margin = area_margin, approx_peri_fraction = approx_peri_fraction, px_dist_to_join = px_dist_to_join)

        BoardTile.create_tiles(img_res, contours)
        #print(contours)

        cv.drawContours(img_res,BoardTile.get_tiles_contours(), -1, (255, 0, 0), 2)
        #print(BoardTile.get_tiles_contours())

        try:
            board = Board(img_res, BoardTile.tiles)

        except Exception:
            print(traceback.format_exc())
            print('========= jestem w main() =============')
        
        print(len(BoardTile.tiles))
        img_res = cv.resize(img_res, (0,0), fx=0.8, fy=0.8)
        cv.imshow("RESULT", img_res)

        # waitKey(0) -> will refresh on button pressed
        # waitkey(x >0) -> will refresh every x millis
        if cv.waitKey(0) == ord('q'): #& 0xFF == ord('q'):
            break



def setup_param_controller():
    cv.namedWindow("Parameters")
    cv.resizeWindow("Parameters", 640, 340)
    cv.createTrackbar("Threshold1", "Parameters", 140, 255, empt_fun)
    cv.createTrackbar("Threshold2", "Parameters", 255, 255, empt_fun)
    cv.createTrackbar("Min_area", "Parameters", 150, 600, empt_fun)
    cv.createTrackbar("Area_margin", "Parameters", 500, 700, empt_fun)
    cv.createTrackbar("Kernel_size", "Parameters", 2, 10, empt_fun)
    cv.createTrackbar("Approx_peri", "Parameters", 3, 50, empt_fun)
    cv.createTrackbar("Px_dist", "Parameters", 15, 100, empt_fun)


if __name__ == '__main__':
    cap = cv.VideoCapture(0)
    cap.open('/dev/v4l/by-id/usb-Xiongmai_web_camera_12345678-video-index0')
    cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter.fourcc(	'M', 'J', 'P', 'G'))
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)

    setup_param_controller()

    main()