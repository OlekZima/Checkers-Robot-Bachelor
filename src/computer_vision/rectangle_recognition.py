import cv2
import numpy as np
from src.checkers_game_and_decisions.utilities import (
    get_pts_dist,
    get_avg_pos,
)


# https://www.youtube.com/watch?v=Fchzk1lDt7Q
def get_contours(
    src, min_area=150, area_margin=20, approx_peri_fraction=0.03, px_dist_to_join=15.0
):
    contours_oryg, hierarchy = cv2.findContours(
        src, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE
    )

    contours_rects_only = []
    contours_approx = np.ndarray((1, 4, 1, 2), dtype=int)

    # STEP 0 - filtering out non quadrangles and gathering rects vertexes

    for cnt in contours_oryg:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, approx_peri_fraction * peri, True)

        if len(approx) == 4:
            contours_rects_only.append(cnt)
            contours_approx = np.append(contours_approx, [approx], axis=0)
            pass

    contours_rects_only = np.array(contours_rects_only, dtype=object)
    contours_approx = contours_approx[
        1:
    ]  # dropping item 0 that was made to initialize the array

    # STEP 1 - filtering out by area being too small and then not close enough to median of all areas

    area_margin = float(area_margin / 100.0)
    if area_margin == 0.0:
        area_margin = 0.01

    keep_cnt = np.zeros(contours_rects_only.shape, dtype=bool)

    for i in range(0, len(contours_rects_only), 1):
        if cv2.contourArea(contours_rects_only[i]) >= min_area:
            keep_cnt[i] = True

    contours_rects_only = contours_rects_only[keep_cnt]
    contours_approx = contours_approx[keep_cnt]

    contours_areas = np.empty(len(contours_rects_only), dtype=int)
    for i in range(0, len(contours_rects_only), 1):
        contours_areas[i] = cv2.contourArea(contours_rects_only[i])

    contours_areas = np.sort(contours_areas, kind="mergesort")

    median_area = contours_areas[int(len(contours_areas) / 2)]
    area_min = int(median_area / area_margin)
    area_max = int(median_area * area_margin)

    keep_cnt = np.zeros(contours_rects_only.shape, dtype=bool)
    for i, cnt in enumerate(contours_rects_only):
        area = cv2.contourArea(cnt)
        if (area >= area_min) and (area <= area_max):
            keep_cnt[i] = True

    # contours_area_filtered = contours_rects_only[keep_cnt]
    contours_approx_area_filtered = contours_approx[keep_cnt]
    # contours_approx_area_filtered = contours_approx

    # STEP 2 - joining points of approximated rectangles in proximity for better grid

    flattened_approx_pnts = np.reshape(
        np.copy(contours_approx_area_filtered), (-1, 1, 1, 2)
    )

    for i, cnt1 in enumerate(flattened_approx_pnts):
        idx_to_avg = [i]
        vals_to_avg = [cnt1[0][0]]
        for j, cntn in enumerate(flattened_approx_pnts[i + 1 :]):
            if get_pts_dist(cnt1[0][0], cntn[0][0]) <= px_dist_to_join:
                idx_to_avg.append(j + i + 1)
                vals_to_avg.append(cntn[0][0])
        avg_pos = get_avg_pos(vals_to_avg)
        for k in idx_to_avg:
            flattened_approx_pnts[k][0][0] = avg_pos

    new_contours_approx_area_filtered = np.reshape(flattened_approx_pnts, (-1, 4, 1, 2))

    # STEP 3 - 2nd time finding countours in syntetic image from these countours that were already found

    # 3.1 - prepare monochrome frame with only contours found above
    syntetic_frame = np.zeros((src.shape[0], src.shape[1]), dtype=np.uint8)
    cv2.drawContours(syntetic_frame, new_contours_approx_area_filtered, -1, (255), 2)
    # syntetic_frame_resized = cv.resize(syntetic_frame,(0,0), fx=0.8, fy=0.8)
    # cv.imshow("Syntetic_frame", syntetic_frame_resized)

    # 3.2 - find countours in those, and filter only quadrangels

    contours_syntetic_frame, hierarchy = cv2.findContours(
        syntetic_frame, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE
    )

    contours_approx_syntetic = np.ndarray((1, 4, 1, 2), dtype=int)
    for cnt in contours_syntetic_frame:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, approx_peri_fraction * peri, True)

        if len(approx) == 4:
            contours_approx_syntetic = np.append(
                contours_approx_syntetic, [approx], axis=0
            )

    contours_approx_syntetic = contours_approx_syntetic[1:]

    # print(contours_approx_syntetic.shape)

    # 3.3 - joining approximate vertexes

    flattened_approx_pnts_syntetic = np.reshape(
        np.copy(contours_approx_syntetic), (-1, 1, 1, 2)
    )

    for i, cnt1 in enumerate(flattened_approx_pnts_syntetic):
        idx_to_avg = [i]
        vals_to_avg = [cnt1[0][0]]
        for j, cntn in enumerate(flattened_approx_pnts_syntetic[i + 1 :]):
            if get_pts_dist(cnt1[0][0], cntn[0][0]) <= px_dist_to_join:
                idx_to_avg.append(j + i + 1)
                vals_to_avg.append(cntn[0][0])
        avg_pos = get_avg_pos(vals_to_avg)
        for k in idx_to_avg:
            flattened_approx_pnts_syntetic[k][0][0] = avg_pos

    flattened_approx_pnts_syntetic = np.reshape(
        flattened_approx_pnts_syntetic, (-1, 4, 1, 2)
    )

    return flattened_approx_pnts_syntetic


def image_prep(img, t1=140, t2=255, kernel=np.ones((3, 3))):
    # cv.imshow("ORIGINAL", img)

    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    img_h, img_s, img_v = cv2.split(img_hsv)
    # cv.imshow("BOARD_RECOGNITION_V_from_HSV", img_v)

    imgCanny = cv2.Canny(img_v, t1, t2)
    # cv.imshow("BOARD_RECOGNITION_CANNY", imgCanny)

    imgDil = cv2.dilate(imgCanny, kernel, iterations=1)
    imgDil_resized = cv2.resize(imgDil, (0, 0), fx=0.8, fy=0.8)
    cv2.imshow("BOARD_RECOGNITION_DILATED", imgDil_resized)

    return imgDil


def get_game_tiles_contours(
    img_src,
    t1=140,
    t2=255,
    kernel=np.ones((2, 2)),
    min_area=150,
    area_margin=20,
    approx_peri_fraction=0.03,
    px_dist_to_join=10.0,
):  # if run from import returns list of chosen game tiles
    img_prepped = image_prep(img_src, t1=t1, t2=t2, kernel=kernel)

    contours = get_contours(
        img_prepped,
        min_area=min_area,
        area_margin=area_margin,
        approx_peri_fraction=approx_peri_fraction,
        px_dist_to_join=px_dist_to_join,
    )

    return contours
