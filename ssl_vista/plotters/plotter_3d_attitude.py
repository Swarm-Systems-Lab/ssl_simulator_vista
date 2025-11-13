__all__ = ["Plotter3DAttitude"]

import numpy as np
import pyvista as pv
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QToolBar, QPushButton, QLabel

from ._base_plotters import BaseVisualPlotter
from .pv_utils.scene_objects import AxesBundle, SphereGridBundle

class Plotter3DAttitude(BaseVisualPlotter):
    """3D Attitude visualizer for a single robot's orientation matrix."""

    def __init__(self, parent=None, label_rot="robot.R", **kwargs):
        super().__init__(parent=parent, **kwargs)
        
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

        # - Static scene objects
        self.obj_axes = None
        self.obj_sphere = None

        # - Connect to context signals
        self.context.robot_focus_changed.connect(self._rotate_axes)
        self.pvqt.keyPressEvent = self.keyPressEvent

    # ------------------------------------------------------------------
    # SCENE SETUP
    # ------------------------------------------------------------------
    def setup_scene(self):
        """Initialize the 3D attitude visualization scene."""
        self.pvqt.set_background("white")
        self.pvqt.show_bounds(grid=True, location="outer", color="black", xtitle="X", ytitle="Y", ztitle="Z")
        self.pvqt.camera_position = "iso"
        self.pvqt.camera.Azimuth(-80)
        self.pvqt.camera.SetParallelProjection(False)
        self.pvqt.enable_3_lights()

        # Add sphere grid and 3 attitude vectors (x, y, z axes)
        self.obj_axes = AxesBundle()
        self.obj_sphere = SphereGridBundle(radius=1.0)
        self.add_scene_object_bundle("axes", self.obj_axes)
        self.add_scene_object_bundle("sphere_grid", self.obj_sphere)
        
        # Set a nice default view
        self.pvqt.reset_camera()

    def reset_scene(self, sim_data=None, sim_settings=None):
        self.num_agents = sim_data[self.label_rot].shape[1]
        self.pvqt.reset_camera()

    # ------------------------------------------------------------------
    # DATA HANDLING
    # ------------------------------------------------------------------
    def _rotate_axes(self):
        """Rotate the axes to match the current robot's orientation."""
        R = self.current_R[self.context.robot_focus, :, :]
        self.obj_axes.transform_to(R=R)

    def update_all_scene_objects(self, sim_data, idx):
        """
        Update attitude visualization from simulation data.

        sim_data[self.label_rot] should have shape (T, N, 3, 3),
        where T = time steps, N = number of robots.
        """
        if self.label_rot not in sim_data:
            raise KeyError(f"sim_data must contain '{self.label_rot}' key for attitude visualization")

        self.current_R = sim_data[self.label_rot][idx, :, :, :]
        self._rotate_axes()
        self.pvqt.render()

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
