"""Module for managing tile grids."""

from __future__ import annotations

from typing import Optional

import cv2 as cv
import numpy as np

from src.common.utils import compute_centroid

from .board_tile import BoardTile


class TileGrid:
    """Manages a collection of BoardTiles, handling creation, connection, and rendering."""

    def __init__(self, frame: Optional[np.ndarray] = None) -> None:
        """Initialize the tile grid.

        Args:
            frame: Optional image frame for rendering connections.
        """
        self.tiles: list[BoardTile] = []
        self.frame = frame

    @classmethod
    def from_contours(cls, image: np.ndarray, contours: np.ndarray) -> TileGrid:
        """Create a TileGrid from detected contours.

        Args:
            image: Source image.
            contours: Array of detected quadrilateral contours.

        Returns:
            Populated TileGrid instance.
        """
        grid = cls(frame=image.copy())
        tile_list: list[BoardTile] = []

        for cnt in contours:
            points = [list(map(int, cnt[i][0])) for i in range(4)]
            tile_list.append(
                BoardTile(vertices=points, center=compute_centroid(points))
            )

        grid.tiles = tile_list
        grid._build_neighbor_graph()

        # Retain only tiles that have at least one neighbor
        grid.tiles = [t for t in grid.tiles if t.neighbors_count >= 1]

        grid._validate_and_render_connections()
        return grid

    def _build_neighbor_graph(self) -> None:
        """Connect neighboring tiles using spatial hashing for efficiency."""
        vertex_to_tiles: dict[tuple[int, int], list[BoardTile]] = {}

        for tile in self.tiles:
            for vertex in tile.vertices:
                vertex_key = (vertex[0], vertex[1])
                if vertex_key not in vertex_to_tiles:
                    vertex_to_tiles[vertex_key] = []
                vertex_to_tiles[vertex_key].append(tile)

        processed_pairs: set[tuple[int, int]] = set()
        for tiles_at_vertex in vertex_to_tiles.values():
            if len(tiles_at_vertex) < 2:
                continue

            for i in range(len(tiles_at_vertex)):
                for j in range(i + 1, len(tiles_at_vertex)):
                    tile1 = tiles_at_vertex[i]
                    tile2 = tiles_at_vertex[j]
                    pair_id = (id(tile1), id(tile2))
                    if pair_id in processed_pairs:
                        continue
                    processed_pairs.add(pair_id)
                    tile1._try_connect_neighbor(tile2)

    def _validate_and_render_connections(self) -> None:
        """Validate neighbor references and draw connection lines on the frame."""
        if self.frame is None:
            return

        tile_ids = {id(t) for t in self.tiles}
        for tile in self.tiles:
            for neighbor_key, neighbor in tile.neighbors.items():
                if neighbor is not None:
                    if id(neighbor) not in tile_ids:
                        tile.neighbors[neighbor_key] = None
                        tile.neighbors_count -= 1
                    else:
                        cv.line(
                            self.frame,
                            (tile.center[0], tile.center[1]),
                            (neighbor.center[0], neighbor.center[1]),
                            (0, 0, 0),
                            1,
                        )

    def extract_contours(self) -> np.ndarray:
        """Extract contours from all tiles in the grid.

        Returns:
            Array of tile contours.
        """
        if not self.tiles:
            return np.array([])

        contours_list = []
        for tile in self.tiles:
            contour = [[[tile.vertices[i]] for i in range(4)]]
            contours_list.append(contour)

        return np.array(contours_list, dtype=int)

    def annotate_center(
        self,
        coordinates: tuple[int, int],
        thickness: int = 3,
        color: tuple[int, int, int] = (0, 0, 255),
        shift: int = 1,
    ) -> None:
        """Draw a circle annotation on the frame.

        Args:
            coordinates: Center coordinates.
            thickness: Circle thickness.
            color: Circle color (BGR).
            shift: Subpixel shift.
        """
        if self.frame is None:
            return
        cv.circle(self.frame, coordinates, thickness, color, shift)
