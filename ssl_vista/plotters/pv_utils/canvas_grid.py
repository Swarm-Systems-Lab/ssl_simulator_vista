__all__ = ["CanvasGrid"]

from os import minor
import numpy as np
from pyparsing import line
import pyvista as pv

class CanvasGrid:
    def __init__(self, pv_plotter, dimension=2, range=None, ticks=None, **kw_box_style):
        """
        Initializes the CanvasGrid object.

        Args:
            pv_plotter (pyvista.Plotter): The PyVista plotter instance.
            dimension (int): The dimensionality of the grid (2 or 3).
            range (tuple): The range of the grid in each dimension.
            ticks (tuple): The number of ticks in each dimension.
        """
        self.pv_plotter = pv_plotter
        self.dimension = dimension
        self.range = range
        self.ticks = ticks
        self.center = np.array([0.0] * dimension)
        self.mesh = None

        # Ensure range and ticks are lists of length 'dimension'
        if isinstance(self.range, (int, float)):
            self.range = [self.range] * self.dimension
        if isinstance(self.ticks, (int, float)):
            self.ticks = [self.ticks] * self.dimension

        # Style configuration for the grid
        kw_box_style.setdefault("font_size", 10)
        kw_box_style.setdefault("xtitle", "X")
        kw_box_style.setdefault("ytitle", "Y")
        kw_box_style.setdefault("ztitle", "Z")
        kw_box_style.setdefault("bold", False)
        kw_box_style.setdefault("color", "black")
        kw_box_style.setdefault("grid", True)
        kw_box_style.setdefault("minor_ticks", True)
        self.kw_style = kw_box_style

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
            location="all",
            n_xlabels=ticks_x, n_ylabels=ticks_y,
            **self.kw_style
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
            n_xlabels=ticks_x, n_ylabels=ticks_y, n_zlabels=ticks_z,
            **self.kw_style
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

    def update_center(self, new_center):
        """
        Updates the center of the grid and adjusts the mesh accordingly.

        Args:
            new_center (np.ndarray): The new center coordinates.
        """
        self.center = new_center

        if self.dimension == 2:
            # Translate the 2D mesh
            translation = self.center - self.mesh.center[:2]
            self.mesh.points[:, :2] += translation
        else:
            # Translate the 3D mesh
            translation = self.center - self.mesh.center
            self.mesh.points += translation

        # Update the bounds and axes to reflect the new center
        self.pv_plotter.update_bounds_axes()

