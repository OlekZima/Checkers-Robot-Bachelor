"""Module for representing board tiles."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from src.common.utils import (
    HALF_PI,
    QUARTER_PI,
    THREE_QUARTER_PI,
    TWO_PI,
    compute_centroid,
)


@dataclass
class BoardTile:
    """Represents a single quadrilateral tile on the checkerboard.

    Attributes:
        vertices: List of 4 [x, y] coordinates defining the tile corners.
        center: (x, y) coordinates of the tile center.
        neighbors: Dictionary mapping neighbor keys to adjacent BoardTile instances.
        neighbors_count: Number of connected neighbors.
        position: (x, y) grid index on the board.
        was_checked_in_dir_idx: Flags tracking checked directions for step counting.
    """

    vertices: list[list[int]]
    center: tuple[int, int]
    neighbors: dict[str, Optional[BoardTile]] = field(default_factory=dict)
    neighbors_count: int = 0
    position: tuple[Optional[int], Optional[int]] = (None, None)
    was_checked_in_dir_idx: list[bool] = field(
        default_factory=lambda: [False, False, False, False]
    )

    NEIGHBORS_KEYS: list[str] = field(
        default_factory=lambda: ["n01", "n12", "n23", "n30"]
    )

    def __post_init__(self) -> None:
        """Initialize neighbor dictionary if not provided."""
        if not self.neighbors:
            self.neighbors = {key: None for key in self.NEIGHBORS_KEYS}

    def set_indexes(self, x: int, y: int) -> None:
        """Set the board grid position of this tile."""
        self.position = (x, y)

    def set_x_index(self, x: int) -> None:
        """Update the x-coordinate of the board grid position."""
        self.position = (x, self.position[1])

    def set_y_index(self, y: int) -> None:
        """Update the y-coordinate of the board grid position."""
        self.position = (self.position[0], y)

    def get_primary_direction(self) -> Optional[float]:
        """Get the direction in radians to the 'n01' neighbor.

        Returns:
            Angle in radians, or None if the neighbor is missing.
        """
        neighbor = self.neighbors.get("n01")
        if neighbor is None:
            return None
        return self.get_angle_to_point(neighbor.center)

    def get_angle_to_point(self, point: Optional[Sequence[int]] = None) -> float:
        """Calculate the angle in radians from this tile's center to a target point.

        Args:
            point: Target (x, y) coordinates. Defaults to origin (0, 0).

        Returns:
            Angle in radians.
        """
        target = point if point is not None else [0, 0]
        dx = target[0] - self.center[0]
        dy = target[1] - self.center[1]

        quadrant_offset, should_swap = self._get_quadrant_offset(dx, dy)
        dx, dy = self._adjust_coordinates(dx, dy, should_swap)

        return self._compute_angle(dx, dy, quadrant_offset)

    def _get_quadrant_offset(self, dx: int, dy: int) -> tuple[float, bool]:
        """Determine the quadrant offset and whether coordinates should be swapped.

        Args:
            dx: Difference in x coordinates.
            dy: Difference in y coordinates.

        Returns:
            Tuple of (radian_offset, should_swap_coordinates).
        """
        if dy < 0 <= dx:
            return HALF_PI, True
        if dx < 0 and dy < 0:
            return math.pi, False
        if dx < 0 <= dy:
            return 3 * HALF_PI, True
        return 0.0, False

    @staticmethod
    def _adjust_coordinates(dx: int, dy: int, should_swap: bool) -> tuple[int, int]:
        """Swap and take absolute values of coordinates based on quadrant.

        Args:
            dx: X difference.
            dy: Y difference.
            should_swap: Flag indicating if coordinates should be swapped.

        Returns:
            Adjusted (dx, dy) as absolute values.
        """
        if should_swap:
            dx, dy = dy, dx
        return abs(dx), abs(dy)

    @staticmethod
    def _compute_angle(dx: int, dy: int, offset: float) -> float:
        """Compute the final angle using atan and quadrant offset.

        Args:
            dx: Adjusted x difference.
            dy: Adjusted y difference.
            offset: Quadrant offset in radians.

        Returns:
            Final angle in radians.
        """
        base_angle = math.atan(dx / dy) if dy != 0 else HALF_PI
        return base_angle + offset

    def _is_point_in_angle_range(
        self, rad_min: float, rad_max: float, point: Optional[Sequence[int]] = None
    ) -> bool:
        """Check if a point lies within a specified angular range.

        Args:
            rad_min: Minimum angle in radians.
            rad_max: Maximum angle in radians.
            point: Target point to check.

        Returns:
            True if the point is within the range.
        """
        if point is None:
            point = [0, 0]

        angle = self.get_angle_to_point(point)

        # Handle wrap-around cases
        return (
            (rad_min <= angle <= rad_max)
            or (angle <= rad_max < rad_min)
            or (rad_max < rad_min <= angle)
        )

    def get_neighbor_in_angle_range(
        self, rad_min: float, rad_max: float
    ) -> Optional[BoardTile]:
        """Find a neighbor tile within a specific angular range.

        Args:
            rad_min: Minimum angle in radians.
            rad_max: Maximum angle in radians.

        Returns:
            The neighbor tile if found, otherwise None.
        """
        for neighbor in self.neighbors.values():
            if neighbor is not None and self._is_point_in_angle_range(
                rad_min, rad_max, neighbor.center
            ):
                return neighbor
        return None

    def get_steps_in_direction(self, dir_rad: float, dir_idx: int) -> int:
        """Count the number of consecutive tiles in a given direction.

        Args:
            dir_rad: Direction angle in radians.
            dir_idx: Index of the direction (0-3).

        Returns:
            Number of steps in the direction.
        """
        if self.was_checked_in_dir_idx[dir_idx]:
            return 0

        self.was_checked_in_dir_idx[dir_idx] = True
        direction_ranges = self._compute_direction_ranges(dir_rad)
        neighbor_steps = self._compute_neighbor_steps(
            direction_ranges, dir_rad, dir_idx
        )

        return max(neighbor_steps, default=0)

    def _compute_direction_ranges(self, dir_rad: float) -> dict[str, float]:
        """Calculate angular boundaries for direction checking.

        Args:
            dir_rad: Base direction angle in radians.

        Returns:
            Dictionary with min/max angles for each search sector.
        """
        return {
            "minus_min": self._normalize_angle(dir_rad - THREE_QUARTER_PI),
            "minus_max": self._normalize_angle(dir_rad - QUARTER_PI),
            "plus_min": self._normalize_angle(dir_rad + QUARTER_PI),
            "plus_max": self._normalize_angle(dir_rad + THREE_QUARTER_PI),
        }

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        """Normalize an angle to the range [0, 2*pi).

        Args:
            angle: Angle in radians.

        Returns:
            Normalized angle.
        """
        if angle < 0:
            return angle + TWO_PI
        if angle >= TWO_PI:
            return angle - TWO_PI
        return angle

    def _compute_neighbor_steps(
        self, ranges: dict[str, float], dir_rad: float, dir_idx: int
    ) -> list[int]:
        """Recursively count steps in the primary and side directions.

        Args:
            ranges: Angular boundaries for search sectors.
            dir_rad: Base direction angle.
            dir_idx: Direction index.

        Returns:
            List of step counts found.
        """
        results = []

        # Check primary direction
        same_dir_neighbor = self.get_neighbor_in_angle_range(
            ranges["minus_max"], ranges["plus_min"]
        )
        if same_dir_neighbor is not None:
            results.append(
                same_dir_neighbor.get_steps_in_direction(dir_rad, dir_idx) + 1
            )

        # Check side directions
        for min_range, max_range in (
            (ranges["minus_min"], ranges["minus_max"]),
            (ranges["plus_min"], ranges["plus_max"]),
        ):
            side_neighbor = self.get_neighbor_in_angle_range(min_range, max_range)
            if side_neighbor is not None:
                results.append(side_neighbor.get_steps_in_direction(dir_rad, dir_idx))

        return results

    def propagate_indexes(self, dir_0: float) -> None:
        """Propagate board grid indexes to all connected neighbors.

        Args:
            dir_0: Primary direction angle in radians.
        """
        dir_01 = self._normalize_angle(dir_0 + QUARTER_PI)
        dir_12 = self._normalize_angle(dir_01 + HALF_PI)
        dir_23 = self._normalize_angle(dir_12 + HALF_PI)
        dir_30 = self._normalize_angle(dir_23 + HALF_PI)

        neighbors_data = [
            (self.get_neighbor_in_angle_range(dir_30, dir_01), (0, -1)),
            (self.get_neighbor_in_angle_range(dir_01, dir_12), (1, 0)),
            (self.get_neighbor_in_angle_range(dir_12, dir_23), (0, 1)),
            (self.get_neighbor_in_angle_range(dir_23, dir_30), (-1, 0)),
        ]

        if self.position[0] is None or self.position[1] is None:
            return

        current_x, current_y = self.position
        assert current_x is not None and current_y is not None

        for neighbor, (dx, dy) in neighbors_data:
            if neighbor is not None and (None in neighbor.position):
                neighbor.set_indexes(current_x + dx, current_y + dy)
                neighbor.propagate_indexes(dir_0)

    def get_vertex_in_angle_range(
        self, rad_min: float, rad_max: float
    ) -> Optional[list[int]]:
        """Find a vertex of this tile within a specific angular range.

        Args:
            rad_min: Minimum angle in radians.
            rad_max: Maximum angle in radians.

        Returns:
            Vertex coordinates if found, otherwise None.
        """
        for vertex in self.vertices:
            if self._is_point_in_angle_range(rad_min, rad_max, vertex):
                return vertex
        return None

    def _try_connect_neighbor(self, other_tile: BoardTile) -> None:
        """Attempt to establish a connection with a neighboring tile.

        Args:
            other_tile: Potential neighbor tile.
        """
        for i, vertex in enumerate(self.vertices):
            for j, other_vertex in enumerate(other_tile.vertices):
                if self._check_vertex_connection(
                    vertex, other_vertex, i, j, other_tile
                ):
                    self._establish_neighbor_link(other_tile, i, j)

    def _check_vertex_connection(
        self,
        vertex: list[int],
        other_vertex: list[int],
        i: int,
        j: int,
        possible_neighbor: BoardTile,
    ) -> bool:
        """Verify if two vertices form a valid connection between tiles.

        Args:
            vertex: Vertex from this tile.
            other_vertex: Vertex from the other tile.
            i: Index of this tile's vertex.
            j: Index of other tile's vertex.
            possible_neighbor: The other tile.

        Returns:
            True if vertices are connected.
        """
        prev_other_idx = (j - 1) % 4
        next_self_idx = (i + 1) % 4

        return (
            vertex[0] == other_vertex[0]
            and vertex[1] == other_vertex[1]
            and self.vertices[next_self_idx][0]
            == possible_neighbor.vertices[prev_other_idx][0]
            and self.vertices[next_self_idx][1]
            == possible_neighbor.vertices[prev_other_idx][1]
        )

    def _establish_neighbor_link(self, neighbor: BoardTile, i: int, j: int) -> None:
        """Register a bidirectional neighbor connection.

        Args:
            neighbor: The connected neighbor tile.
            i: Index of this tile's vertex.
            j: Index of neighbor's vertex.
        """
        prev_other_idx = (j - 1) % 4

        for key in self.NEIGHBORS_KEYS:
            index = int(key[1])

            if i == index:
                self.neighbors[key] = neighbor
            if prev_other_idx == index:
                neighbor.neighbors[key] = self

        self.neighbors_count += 1
        neighbor.neighbors_count += 1
