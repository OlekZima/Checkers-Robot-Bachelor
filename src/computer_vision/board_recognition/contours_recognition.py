"""Module for detecting contours on the board. Contains ContourProcessor class."""

from typing import Optional, Tuple
import cv2
import numpy as np
from ...common.utilities import get_pts_dist
from src.common.dataclasses import RecognitionConfig


class ContourProcessor:
    """Helper class for contours detection on the board."""

    def __init__(self, recognition_config: Optional[RecognitionConfig] = None):
        """Constructor for the ContourProcessor class.

        Args:
            config (Optional[RecognitionConfig], optional):
                dataclass that consists of following attributes:

                min_area: int = 150
                area_margin: int = 20
                approx_peri_fraction: float = 0.03
                px_dist_to_join: float = 15.0
                threshold1: int = 140
                threshold2: int = 255
                kernel_size: Tuple[int, int] = (2, 2)


                Defaults to None.
        """
        self.recognition_config: RecognitionConfig = (
            recognition_config or RecognitionConfig()
        )
        self.kernel = np.ones(self.recognition_config.kernel_size)

    def get_contours(
        self, image: np.ndarray, recognition_config: Optional[RecognitionConfig] = None
    ) -> np.ndarray:
        self.recognition_config = (
            recognition_config
            if recognition_config is not None
            else self.recognition_config
        )

        preprocessed_img = self._preprocess_image(image)
        contours = self._detect_contours(preprocessed_img)

        return contours

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        img_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        _, _, img_v = cv2.split(img_hsv)

        img_canny = cv2.Canny(
            img_v,
            self.recognition_config.threshold1,
            self.recognition_config.threshold2,
        )
        img_dil = cv2.dilate(img_canny, self.kernel, iterations=1)

        return img_dil

    def _detect_contours(self, image: np.ndarray) -> np.ndarray:
        """Detect and process contours on the image.

        Args:
            image (np.ndarray): an image to process

        Returns:
            np.ndarray: processed contours
        """
        initial_contours = self._find_quadrilateral_contours(image)
        filtered_contours = self._filter_contours_by_area(initial_contours)
        joined_contours = self._join_nearby_points(filtered_contours)
        synthetic_contours = self._reprocess_synthetic_image(
            joined_contours, image.shape
        )
        return synthetic_contours

    def _find_quadrilateral_contours(self, image: np.ndarray) -> np.ndarray:
        """Function that finds quadrilateral contours on the image.

        Args:
            image (np.ndarray): image to process

        Returns:
            np.ndarray: quadrilateral contours found on the image
        """

        contours, _ = cv2.findContours(image, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

        quad_contours = np.ndarray((1, 4, 1, 2), dtype=int)
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(
                contour, self.recognition_config.approx_peri_fraction * perimeter, True
            )
            if len(approx) == 4:
                approx = approx.reshape(1, 4, 1, 2)
                quad_contours = np.append(quad_contours, approx, axis=0)

        return quad_contours[1:] if len(quad_contours) > 1 else np.array([])

    def _filter_contours_by_area(self, contours: np.ndarray) -> np.ndarray:
        if len(contours) == 0:
            return np.array([])

        areas = np.array(
            [cv2.contourArea(contour.reshape(-1, 1, 2)) for contour in contours]
        )

        min_area_mask = areas >= self.recognition_config.min_area
        contours = contours[min_area_mask]
        areas = areas[min_area_mask]

        if len(areas) == 0:
            return np.array([])

        median_area = np.median(areas)
        margin = self.recognition_config.area_margin_percent / 100
        area_min = median_area / (1 + margin)
        area_max = median_area * (1 + margin)

        area_margin_mask = (areas >= area_min) & (areas <= area_max)
        return contours[area_margin_mask]

    def _join_nearby_points(self, contours: np.ndarray) -> np.ndarray:
        if len(contours) == 0:
            return np.array([])

        flattened_points = contours.reshape(-1, 1, 1, 2)

        for i, point1 in enumerate(flattened_points):
            points_to_join = [point1[0][0]]
            indices_to_update = [i]

            for j, point2 in enumerate(flattened_points[i + 1 :], i + 1):
                if (
                    get_pts_dist(point1[0][0], point2[0][0])
                    <= self.recognition_config.px_dist_to_join
                ):
                    points_to_join.append(point2[0][0])
                    indices_to_update.append(j)

            if len(points_to_join) > 1:
                avg_x = sum(point[0] for point in points_to_join) // len(points_to_join)
                avg_y = sum(point[1] for point in points_to_join) // len(points_to_join)

                for idx in indices_to_update:
                    flattened_points[idx][0][0] = np.array([avg_x, avg_y])

        return flattened_points.reshape(-1, 4, 1, 2)

    def _reprocess_synthetic_image(
        self, contours: np.ndarray, image_shape: Tuple[int, int]
    ) -> np.ndarray:
        syntetic_image = np.zeros(image_shape, dtype=np.uint8)
        cv2.drawContours(syntetic_image, contours, -1, (255), 2)

        reprocessed_contours = self._find_quadrilateral_contours(syntetic_image)
        return self._join_nearby_points(reprocessed_contours)


if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    configuration = RecognitionConfig()
    image_processor = ContourProcessor(configuration)
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        contours_frame = image_processor.get_contours(frame)
        cv2.drawContours(frame, contours_frame, -1, (0, 255, 0), 2)
        cv2.imshow("CONTOURS", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()
