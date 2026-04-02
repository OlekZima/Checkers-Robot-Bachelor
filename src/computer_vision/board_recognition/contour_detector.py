"""Module for detecting quadrilateral contours on a board image."""

from typing import List, Optional, Tuple

import cv2 as cv
import numpy as np

from src.common.configs import RecognitionConfig


class ContourDetector:
    """Detects and processes quadrilateral contours from an input image.

    This class applies image preprocessing, contour detection, filtering,
    and point refinement to identify board tiles.
    """

    def __init__(self, config: Optional[RecognitionConfig] = None) -> None:
        """Initialize the detector with an optional configuration.

        Args:
            config: Recognition configuration parameters. Defaults to standard settings.
        """
        self.config: RecognitionConfig = config or RecognitionConfig()
        self._kernel: np.ndarray = np.ones(self.config.kernel_size, dtype=np.uint8)

    def detect(
        self, image: np.ndarray, config: Optional[RecognitionConfig] = None
    ) -> np.ndarray:
        """Detect quadrilateral contours in the given image.

        Args:
            image: Input BGR image.
            config: Optional configuration override for this detection run.

        Returns:
            Array of detected quadrilateral contours with shape (N, 4, 1, 2).
        """
        if config is not None:
            self.config = config
            self._kernel = np.ones(self.config.kernel_size, dtype=np.uint8)

        preprocessed = self._preprocess_image(image)
        return self._process_contours(preprocessed)

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale via HSV and apply edge detection.

        Args:
            image: Input BGR image.

        Returns:
            Dilated edge map.
        """
        hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)
        value_channel = hsv_image[:, :, 2]

        edges = cv.Canny(
            value_channel,
            self.config.threshold1,
            self.config.threshold2,
        )
        return cv.dilate(edges, self._kernel, iterations=1)

    def _process_contours(self, edge_map: np.ndarray) -> np.ndarray:
        """Orchestrate the contour detection and refinement pipeline.

        Args:
            edge_map: Preprocessed edge image.

        Returns:
            Refined quadrilateral contours.
        """
        quad_contours = self._extract_quadrilaterals(edge_map)
        area_filtered = self._filter_by_area(quad_contours)
        joined_points = self._merge_nearby_vertices(area_filtered)
        return self._refine_on_synthetic_image(joined_points, edge_map.shape)

    def _extract_quadrilaterals(self, edge_map: np.ndarray) -> np.ndarray:
        """Find all contours and keep only those approximating quadrilaterals.

        Args:
            edge_map: Preprocessed edge image.

        Returns:
            Array of quadrilateral contours.
        """
        raw_contours, _ = cv.findContours(
            edge_map, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE
        )
        tolerance = self.config.approx_peri_fraction

        quad_contours: List[np.ndarray] = []
        for contour in raw_contours:
            perimeter = cv.arcLength(contour, closed=True)
            approx = cv.approxPolyDP(contour, tolerance * perimeter, closed=True)
            if len(approx) == 4:
                quad_contours.append(approx.reshape(1, 4, 1, 2))

        return np.vstack(quad_contours) if quad_contours else np.array([])

    def _filter_by_area(self, contours: np.ndarray) -> np.ndarray:
        """Filter contours based on area relative to the median area.

        Args:
            contours: Array of quadrilateral contours.

        Returns:
            Contours within the acceptable area range.
        """
        if len(contours) == 0:
            return np.array([])

        areas = np.array([cv.contourArea(c.reshape(-1, 1, 2)) for c in contours])

        # Remove very small contours
        valid_mask = areas >= self.config.min_area
        contours = contours[valid_mask]
        areas = areas[valid_mask]

        if len(areas) == 0:
            return np.array([])

        # Filter around median area
        median_area = np.median(areas)
        margin_ratio = self.config.area_margin_percent / 100.0
        area_min = median_area / (1.0 + margin_ratio)
        area_max = median_area * (1.0 + margin_ratio)

        area_mask = (areas >= area_min) & (areas <= area_max)
        return contours[area_mask]

    def _merge_nearby_vertices(self, contours: np.ndarray) -> np.ndarray:
        """Merge vertices that are closer than the configured distance threshold.

        Uses spatial hashing for O(n) average complexity.

        Args:
            contours: Array of quadrilateral contours.

        Returns:
            Contours with merged vertices.
        """
        if len(contours) == 0:
            return np.array([])

        points = contours.reshape(-1, 2).copy()
        join_distance = self.config.px_dist_to_join
        join_distance_sq = join_distance**2
        cell_size = join_distance

        # Build spatial hash grid
        grid: dict[Tuple[int, int], List[int]] = {}
        point_cell_map: List[Tuple[int, int]] = []

        for idx, (x, y) in enumerate(points):
            cell_x = int(x // cell_size)
            cell_y = int(y // cell_size)
            cell_key = (cell_x, cell_y)
            point_cell_map.append(cell_key)

            if cell_key not in grid:
                grid[cell_key] = []
            grid[cell_key].append(idx)

        merged_mask = np.zeros(len(points), dtype=bool)

        for i in range(len(points)):
            if merged_mask[i]:
                continue

            cell_x, cell_y = point_cell_map[i]
            cluster_indices = [i]

            # Check 3x3 neighborhood
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    neighbor_cell = (cell_x + dx, cell_y + dy)
                    if neighbor_cell not in grid:
                        continue

                    for j in grid[neighbor_cell]:
                        if j <= i or merged_mask[j]:
                            continue

                        dist_sq = (points[i, 0] - points[j, 0]) ** 2 + (
                            points[i, 1] - points[j, 1]
                        ) ** 2
                        if dist_sq <= join_distance_sq:
                            cluster_indices.append(j)

            if len(cluster_indices) > 1:
                avg_point = np.mean(points[cluster_indices], axis=0).astype(int)
                for idx in cluster_indices:
                    points[idx] = avg_point
                    merged_mask[idx] = True

        return points.reshape(-1, 4, 1, 2)

    def _refine_on_synthetic_image(
        self, contours: np.ndarray, original_shape: Tuple[int, ...]
    ) -> np.ndarray:
        """Draw contours on a blank image and re-detect to clean up noise.

        Args:
            contours: Refined quadrilateral contours.
            original_shape: Shape of the original input image.

        Returns:
            Final cleaned quadrilateral contours.
        """
        if len(contours) == 0:
            return np.array([])

        synthetic = np.zeros(original_shape[:2], dtype=np.uint8)
        cv.drawContours(synthetic, contours.astype(np.int32), -1, 255, 2)

        redetected = self._extract_quadrilaterals(synthetic)
        return self._merge_nearby_vertices(redetected)


if __name__ == "__main__":
    cap = cv.VideoCapture(0)
    detector = ContourDetector()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        detected_contours = detector.detect(frame)
        cv.drawContours(
            frame, [c.astype(np.int32) for c in detected_contours], -1, (0, 255, 0), 2
        )
        cv.imshow("Detected Contours", frame)

        if cv.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv.destroyAllWindows()
