__all__ = ["BaseCanvasPlotter"]

import numpy as np
import pyvista as pv

from ._base_plotters import _BaseVisualPlotter
from .pv_utils.canvas_grid import CanvasGrid
from .pv_utils.configs import CameraConfig, GraphicsConfig, GridConfig, RobotConfig
from .pv_utils.scene import Robot2D, Robot3D


def apply_camera(pvqt, cam: dict) -> None:
    """Apply a resolved :class:`CameraConfig` (see ``CameraConfig.resolved``) to a plotter."""
    pvqt.set_background(cam["background"])
    pvqt.camera_position = cam["position"]
    pvqt.camera.SetParallelProjection(cam["parallel"])
    if cam["lights"] == "2d":
        pvqt.enable_2d_style()
    elif cam["lights"] == "three":
        pvqt.enable_3_lights()
    if cam["azimuth"] is not None:
        pvqt.camera.Azimuth(cam["azimuth"])


class BaseCanvasPlotter(_BaseVisualPlotter):
    """
    Generalized PyVista canvas for spatial visualization.

    Configuration is grouped into namespaces — ``grid`` (:class:`GridConfig`),
    ``camera`` (:class:`CameraConfig`), ``robot`` (:class:`RobotConfig`) and
    ``graphics`` (:class:`GraphicsConfig`) — each accepting a model or a plain dict
    (e.g. from a layout file's ``args``). Each namespace is forwarded whole to its
    sub-component, so options never need re-declaring on this class.

    Subclasses should:
      - Implement `init_artists(self, sim_data, sim_settings)` to define the scene's artists.
      - Implement `update_artists(self, sim_data, idx)` to update the scene's artists.
    """

    def __init__(
        self,
        dimension,  # 2 or 3
        *,
        parent=None,
        context=None,
        sim_data_labels=None,
        grid=None,
        camera=None,
        robot=None,
        graphics=None,
    ):
        super().__init__(parent=parent, context=context)

        self.dimension = dimension
        self._robot_objs = []
        self.sim_data_labels = sim_data_labels or {"positions": "robot.p", "rotations": "robot.R"}

        # - Config namespaces (each accepts a model, a dict, or None)
        self.grid_config = GridConfig.build(grid)
        self.camera_config = CameraConfig.build(camera)
        self.graphics = GraphicsConfig.build(graphics)
        self.robot_config = RobotConfig.build(robot)

        # - Canvas grid (whole grid namespace forwarded)
        self.canvas_grid = CanvasGrid(self.pvqt, dimension=dimension, config=self.grid_config)

    # ---------------------------------------------------------------
    # ARTISTS MANAGEMENT
    # ---------------------------------------------------------------

    def _clear_artists(self):
        """Remove all artists from the scene."""
        self.clear_scene_objects()
        self._robot_objs.clear()

    # ---------------------------------------------------------------
    # CANVAS HELPER METHODS
    # ---------------------------------------------------------------
    def add_robot(self, robot_name, icon_type, visible=True, traj_max_len=None, **kwargs):
        # - Create the robot bundle (trajectory tail self-trims to traj_max_len)
        robot_cls = Robot2D if self.dimension == 2 else Robot3D
        obj_robot = robot_cls(
            icon_type,
            visible=visible,
            traj_max_len=traj_max_len,
            graphics=self.graphics,
            **kwargs,
        )

        self.add_scene_object(robot_name, obj_robot)
        self._robot_objs.append(obj_robot)
        return obj_robot

    def set_grid_centroid(self, centroid):
        """Set the canvas grid centroid."""
        self.canvas_grid.update_center(centroid)

    # ---------------------------------------------------------------
    # SETUP/RESET/UPDATE SCENE
    # ---------------------------------------------------------------
    def setup_scene(self, sim_data=None, sim_settings=None):
        """Set up the scene by initializing the grid and artists."""
        apply_camera(self.pvqt, self.camera_config.resolved(self.dimension))

        # Add a reference grid
        self.canvas_grid.setup_grid()

        # Reset camera
        self.pvqt.reset_camera()

    def reset_scene(self, sim_data=None, sim_settings=None):
        """Reset the scene by clearing and reinitializing artists."""
        self._clear_artists()
        self.init_artists(sim_data, sim_settings)
        self.pvqt.reset_camera()

    def reset_view(self) -> None:
        """Restore initial camera orientation, grid position, and fit the scene."""
        self.canvas_grid.reset()
        cam = self.camera_config.resolved(self.dimension)
        self.pvqt.camera_position = cam["position"]
        self.pvqt.camera.SetParallelProjection(cam["parallel"])
        self.pvqt.reset_camera()

    # ---------------------------------------------------------------
    # SCENE OBJECTS MANAGEMENT
    # ---------------------------------------------------------------
    def get_scene_object(self, obj_name):
        """Retrieve a scene object by name."""
        return self.scene_objects.get(obj_name, None)

    def in_scene(self, names):
        """Check if one or more scene objects exist."""
        if not isinstance(names, (str, tuple)):
            raise TypeError("names must be a string or a tuple of strings")
        if isinstance(names, tuple):
            return all(name in self.scene_objects for name in names)
        return names in self.scene_objects

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
