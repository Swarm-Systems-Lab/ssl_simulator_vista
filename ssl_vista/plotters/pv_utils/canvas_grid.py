__all__ = ["CanvasGrid"]

from os import minor
import numpy as np
import pyvista as pv

class CanvasGrid:
    def __init__(self, pv_plotter, dimension=2, range=None, ticks=None):
        self.pv_plotter = pv_plotter # PyVista plotter

        self.dimension = dimension
        self.range = range
        self.ticks = ticks
        self.center = np.array([0.0] * dimension)
        self.mesh = None

    def _create_2d(self):
        range_x, range_y = self.range
        ticks_x, ticks_y = self.ticks
        self.mesh = pv.Plane(i_size=range_x, j_size=range_y, i_resolution=2, j_resolution=2)
        self.pv_plotter.add_mesh(
            self.mesh, 
            color="lightgray", 
            style="wireframe", 
            opacity=0.0
        )
        self.pv_plotter.show_bounds(
            grid=True, 
            location="all", 
            color="black", 
            xtitle="X", ytitle="Y", 
            minor_ticks=True, 
            n_xlabels=ticks_x, n_ylabels=ticks_y
        )
        

    def _create_3d(self):
        range_x, range_y, range_z = self.range
        ticks_x, ticks_y, ticks_z = self.ticks
        self.mesh = pv.Box(bounds=(-range_x, range_x, -range_y, range_y, -range_z, range_z))
        self.pv_plotter.add_mesh(
            self.mesh, 
            color="lightgray", 
            style="wireframe", 
            opacity=0.0
        )
        self.pv_plotter.show_bounds(
            grid=True, 
            location="outer", 
            color="black", 
            xtitle="X", ytitle="Y", ztitle="Z",
            minor_ticks=True,
            n_xlabels=ticks_x, n_ylabels=ticks_y, n_zlabels=ticks_z
        )

    def setup_grid(self):
        if self.dimension == 2:
            self._create_2d()
        else:
            self._create_3d()
        self.pv_plotter.reset_camera()
    
    def update_center(self, new_center):
        self.center = new_center
        if self.dimension == 2:
            translation = self.center - self.mesh.center[:2]
            self.mesh.points[:, :2] += translation
        else:
            translation = self.center - self.mesh.center
            self.mesh.points += translation
        self.pv_plotter.update_bounds_axes()

