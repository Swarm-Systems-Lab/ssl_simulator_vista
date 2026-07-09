__all__ = ["CanvasGrid"]

import numpy as np
import pyvista as pv

from .configs import GridConfig


class CanvasGrid:
    def __init__(self, pv_plotter, dimension=2, config: GridConfig | dict | None = None):
        """
        Initializes the CanvasGrid object.

        Args:
            pv_plotter (pyvista.Plotter): The PyVista plotter instance.
            dimension (int): The dimensionality of the grid (2 or 3).
            config (GridConfig | dict | None): Grid range, ticks, and label style.
        """

        self.pv_plotter = pv_plotter
        self.dimension = dimension
        self.config = GridConfig.build(config)

        # Range/ticks: default to 5, and broadcast a scalar across every dimension.
        grid_range = self.config.range if self.config.range is not None else 5
        ticks = self.config.ticks if self.config.ticks is not None else 5
        if isinstance(grid_range, (int, float)):
            grid_range = [grid_range] * dimension
        if isinstance(ticks, (int, float)):
            ticks = [ticks] * dimension
        self.range = grid_range
        self.ticks = ticks
        self.center = np.array([0.0] * dimension)
        self.mesh = None

        # Style forwarded to show_bounds (font, titles, color, grid, minor ticks).
        self.kw_style = self.config.show_bounds_style()

    def _create_2d(self):
        """
        Creates a 2D grid and sets up the bounds for the plotter.
        """
        range_x, range_y = self.range
        ticks_x, ticks_y = self.ticks

        # Create an invisible 2D plane mesh
        self.mesh = pv.Plane(i_size=range_x, j_size=range_y, i_resolution=2, j_resolution=2)
        self.pv_plotter.add_mesh(self.mesh, opacity=0.0)

        # Configure the bounds and axes
        self.pv_plotter.show_bounds(
            location="all", n_xlabels=ticks_x, n_ylabels=ticks_y, **self.kw_style
        )

    def _create_3d(self):
        """
        Creates a 3D grid and sets up the bounds for the plotter.
        """
        range_x, range_y, range_z = self.range
        ticks_x, ticks_y, ticks_z = self.ticks

        # Create an invisible 3D box mesh
        self.mesh = pv.Box(bounds=(-range_x, range_x, -range_y, range_y, -range_z, range_z))
        self.pv_plotter.add_mesh(self.mesh, opacity=0.0)

        # Configure the bounds and axes
        self.pv_plotter.show_bounds(
            location="outer",
            n_xlabels=ticks_x,
            n_ylabels=ticks_y,
            n_zlabels=ticks_z,
            **self.kw_style,
        )

    def setup_grid(self):
        """
        Sets up the grid based on the specified dimension.
        """
        if self.dimension == 2:
            self._create_2d()
        else:
            self._create_3d()
        self.pv_plotter.reset_camera()

    def _sync_axes_bounds(self) -> None:
        """Push the grid mesh bounds to the CubeAxesActor.

        pv_plotter.update_bounds_axes() recomputes from ALL visible actors, so
        it expands whenever robots drift near the edge. Calling update_bounds()
        directly on the actor limits the labels to the grid mesh only.
        """
        actor = self.pv_plotter.renderer.cube_axes_actor
        if actor is not None and self.mesh is not None:
            actor.update_bounds(self.mesh.bounds)

    def reset(self) -> None:
        """Sync the CubeAxesActor bound to the grid mesh."""
        if self.mesh is None:
            return
        self._sync_axes_bounds()

    def update_center(self, new_center):
        """
        Updates the center of the grid and adjusts the mesh accordingly.

        Args:
            new_center (np.ndarray): The new center coordinates (any shape; first
                ``dimension`` elements are used).
        """
        arr = np.asarray(new_center, dtype=float).reshape(-1)

        if self.dimension == 2:
            # Translate the 2D mesh
            self.center = arr[:2]
            translation = self.center - self.mesh.center[:2]
            self.mesh.points[:, :2] += translation
        else:
            # Translate the 3D mesh; pad to 3 elements if a 2D centroid was supplied
            center3 = np.zeros(3)
            n = min(3, len(arr))
            center3[:n] = arr[:n]
            self.center = center3
            translation = self.center - self.mesh.center
            self.mesh.points += translation

        # Update the bounds and axes to reflect the new center
        self.pv_plotter.update_bounds_axes()
