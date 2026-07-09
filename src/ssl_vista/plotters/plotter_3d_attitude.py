__all__ = ["Plotter3DAttitude"]

import numpy as np
import pyvista as pv
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QLabel, QPushButton, QToolBar, QVBoxLayout, QWidget
from ssl_simulator.math import check_and_parse_dimensions

from ._base_plotters import _BaseVisualPlotter
from .base_canvas import apply_camera
from .pv_utils.canvas_grid import CanvasGrid
from .pv_utils.configs import CameraConfig, GridConfig
from .pv_utils.scene import Axes, SphereGrid


class Plotter3DAttitude(_BaseVisualPlotter):
    """3D Attitude visualizer for a single robot's orientation matrix."""

    def __init__(self, *, parent=None, context=None, label_rot="robot.R", grid=None, camera=None):
        super().__init__(parent=parent, context=context)

        # --- CUSTOM WIDGET SETUP ---
        custom_widget = QWidget(parent)
        layout = QVBoxLayout(custom_widget)

        # Add a toolbar at the top
        toolbar = QToolBar(custom_widget)
        layout.addWidget(toolbar)

        if self.context.robot_focus is None:
            self.context.robot_focus = 0
        self.label = QLabel(f"Robot idx: {self.context.robot_focus}", custom_widget)
        toolbar.addWidget(self.label)

        # Add the plotter (self) below the toolbar
        layout.addWidget(self.get_widget())
        self.set_widget(custom_widget)
        # ---------------------------

        # - Simulation data info (updated dynamically when sim_data is provided)
        self.num_agents = 1
        self.current_R = np.eye(3)

        # - Simulation data labels
        self.label_rot = label_rot

        # - Config namespaces (attitude defaults: unit grid, iso view azimuth -80)
        self.grid_config = GridConfig.build(grid, range=1, ticks=5)
        self.camera_config = CameraConfig.build(camera, azimuth=-80)

        # - Static scene objects
        self.obj_axes = None
        self.obj_sphere = None
        self.canvas_grid = CanvasGrid(self.pvqt, dimension=3, config=self.grid_config)

        # - Connect to context signals
        self.context.robot_focus_changed.connect(self._rotate_axes)

    # ------------------------------------------------------------------
    # SCENE SETUP
    # ------------------------------------------------------------------
    def setup_scene(self):
        """Set up the camera, lights, and reference grid (data-independent)."""
        apply_camera(self.pvqt, self.camera_config.resolved(3))

        # Add a 3D reference grid
        self.canvas_grid.setup_grid()

        # Set a nice default view
        self.pvqt.reset_camera()

    # ------------------------------------------------------------------
    # ARTISTS
    # ------------------------------------------------------------------
    def init_artists(self, sim_data, sim_settings):
        """Create the sphere grid and the x/y/z attitude axes."""
        if self.label_rot not in sim_data:
            raise KeyError(
                f"sim_data must contain '{self.label_rot}' key for attitude visualization"
            )
        data_rot = check_and_parse_dimensions(
            sim_data[self.label_rot], (None, None, 3, 3), "rotation matrix"
        )
        self.num_agents = data_rot.shape[1]

        self.obj_axes = Axes()
        self.obj_sphere = SphereGrid(radius=1.0)
        self.add_scene_object("axes", self.obj_axes)
        self.add_scene_object("sphere_grid", self.obj_sphere)

    def update_artists(self, sim_data, idx):
        """
        Update attitude visualization from simulation data.

        sim_data[self.label_rot] should have shape (T, N, 3, 3),
        where T = time steps, N = number of robots.
        """
        # FIXME: this will be inefficient, data should come formatted.
        #        We need a better way to handle dimensionality with multiple robots and
        #        timesteps without forcing users to pre-format data in a specific way.
        data_rot = check_and_parse_dimensions(
            sim_data[self.label_rot], (None, None, 3, 3), "rotation matrix"
        )
        self.num_agents = data_rot.shape[1]
        self.current_R = data_rot[idx, :, :, :]
        self._rotate_axes()

    # ------------------------------------------------------------------
    # DATA HANDLING
    # ------------------------------------------------------------------
    def _rotate_axes(self):
        """Rotate the axes to match the current robot's orientation."""
        if self.obj_axes is None:
            return
        R = self.current_R[self.context.robot_focus, :, :]
        self.obj_axes.set_pose(R=R)

    # ------------------------------------------------------------------
    # KEYBOARD CONTROL
    # ------------------------------------------------------------------
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Use PageUp/PageDown to switch between robots."""
        key = event.key()
        if key == QtCore.Qt.Key_PageDown:
            if self.num_agents > 0:
                self.context.robot_focus = (self.context.robot_focus - 1) % self.num_agents
                self.label.setText(f"Robot idx: {self.context.robot_focus}")
                self.pvqt.render()
        elif key == QtCore.Qt.Key_PageUp:
            if self.num_agents > 0:
                self.context.robot_focus = (self.context.robot_focus + 1) % self.num_agents
                self.label.setText(f"Robot idx: {self.context.robot_focus}")
                self.pvqt.render()
        elif key == QtCore.Qt.Key_R:
            self.pvqt.reset_camera()
        event.accept()
