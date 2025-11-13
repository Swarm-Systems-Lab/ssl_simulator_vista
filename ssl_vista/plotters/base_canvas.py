__all__ = ["Plotter3DCanvas"]

from os import name
import numpy as np
import pyvista as pv

from ._base_plotters import BaseVisualPlotter
from .pv_utils.canvas_grid import CanvasGrid
from .pv_utils.scene_objects import Robot2D, Robot3D

class BaseCanvasPlotter(BaseVisualPlotter):
    """
    Generalized PyVista canvas for spatial visualization.

    Subclasses should:
      - Implement `init_artists(self, sim_data, sim_settings)` to define the scene's artists.
      - Implement `update_artists(self, sim_data, idx)` to update the scene's artists.
    """

    def __init__(
        self,
        dimension, # 2 or 3
        parent=None,
        sim_data_labels=None,
        canvas_grid_range=None,
        canvas_grid_ticks=None,
        **kwargs
    ):
        super().__init__(parent=parent, **kwargs)
        
        self.dimension = dimension
        self.sim_data_labels = sim_data_labels or {}
        self._robot_objs = []

        # - Simulation data labels
        if sim_data_labels is None:
            sim_data_labels = {"positions": "robot.p", "rotations": "robot.R"}
        self.sim_data_labels = sim_data_labels

        # - Canvas grid
        if canvas_grid_range is None:
            canvas_grid_range = [5, 5] if dimension == 2 else [5, 5, 5]
        if canvas_grid_ticks is None:
            canvas_grid_ticks = [11, 11] if dimension == 2 else [11, 11, 11]

        self.canvas_grid = CanvasGrid(self.pvqt, dimension=dimension, range=canvas_grid_range, ticks=canvas_grid_ticks)

    # ---------------------------------------------------------------
    # SETUP/RESET SCENE
    # ---------------------------------------------------------------
    def setup_scene(self, sim_data=None, sim_settings=None):
        """Set up the scene by initializing the grid and artists."""
        self.pvqt.set_background("white")

        if self.dimension == 2:
            self.pvqt.set_background("white")
            self.pvqt.camera_position = "xy"
            self.pvqt.camera.SetParallelProjection(True)
            self.pvqt.enable_2d_style()
        else:
            self.pvqt.camera_position = "iso"
            self.pvqt.camera.Azimuth(-90)
            self.pvqt.camera.SetParallelProjection(False)
            self.pvqt.enable_3_lights()

        # Add a 3D reference grid
        self.canvas_grid.setup_grid()

        # Reset camera
        self.pvqt.reset_camera()

    def reset_scene(self, sim_data=None, sim_settings=None):
        """Reset the scene by clearing and reinitializing artists."""
        self.clear_artists()
        self.init_artists(sim_data, sim_settings)
        self.print_scene_objects()
        self.pvqt.reset_camera()

    # ---------------------------------------------------------------
    # ARTISTS MANAGEMENT
    # ---------------------------------------------------------------
    def init_artists(self, sim_data, sim_settings):
        """
        Initialize the scene's artists. Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement `init_artists`.")

    def update_artists(self, sim_data, idx):
        """
        Update the scene's artists. Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement `update_artists`.")

    def clear_artists(self):
        """Remove all artists from the scene."""
        for name, obj in self.scene_objects.items():
            self.remove_scene_object(name)
        self.scene_objects.clear()

    # ---------------------------------------------------------------
    # CANVAS HELPER METHODS
    # ---------------------------------------------------------------
    def add_robot(self, name, icon_type, visible=True, **kwargs):
        # - Create the robot mesh
        if self.dimension == 2:
            obj_robot = Robot2D(icon_type, visible=visible, **kwargs)
        else:
            obj_robot = Robot3D(icon_type, visible=visible, **kwargs)

        self.add_scene_object_bundle(name, obj_robot)
        self._robot_objs.append(obj_robot)
        return obj_robot

    def set_grid_centroid(self, centroid):
        """Set the canvas grid centroid."""
        self.canvas_grid.update_center(centroid)
    
    # ---------------------------------------------------------------
    # SCENE OBJECTS MANAGEMENT
    # ---------------------------------------------------------------
    def get_scene_object(self, name):
        """Retrieve a scene object by name."""
        return self.scene_objects.get(name, None)
    
    def get_robot_objects(self, robot_name):
        """Retrieve the robot and its trajectory objects."""
        obj = self.get_scene_object(robot_name)
        if obj is None:
            return None, None
        return self.get_scene_object(robot_name), self.get_scene_object(robot_name+".traj")

    def in_scene(self, names):
        """Check if one or more scene objects exist."""
        if not isinstance(names, (str, tuple)):
            raise TypeError("names must be a string or a tuple of strings")
        if isinstance(names, tuple):
            return all(name in self.scene_objects for name in names)
        return names in self.scene_objects
    
    def update_all_scene_objects(self, sim_data, idx):
        """Update all artists in the scene."""
        self.update_artists(sim_data, idx)
        self.pvqt.render()

    # ---------------------------------------------------------------
    # CONTEXT SIGNALS CALLBACKS
    # ---------------------------------------------------------------
    # To be modified by subclasses if needed
    def when_change_robot_focus(self, idx_new_focus, idx_prv_focus):
        """Handle changes in robot focus from the context."""
        if idx_new_focus is not None and len(self._robot_objs) > idx_new_focus:
            if idx_prv_focus is not None and len(self._robot_objs) > idx_prv_focus:
                self._robot_objs[idx_prv_focus].set_focus(False)
            self._robot_objs[idx_new_focus].set_focus(True)