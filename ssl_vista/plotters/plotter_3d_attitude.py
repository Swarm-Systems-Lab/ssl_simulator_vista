__all__ = ["Plotter3DAttitude"]

import numpy as np
import pyvista as pv
from PyQt5 import QtCore, QtGui

from ._base_plotters import BaseVisualPlotter
from .meshes import create_sphere_grid, create_geodesic, make_dashed_line
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QToolBar, QPushButton, QLabel

class Plotter3DAttitude(BaseVisualPlotter):
    """3D Attitude visualizer for a single robot's orientation matrix."""

    def __init__(self, parent=None, R_label="robot.R", **kwargs):
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
        layout.addWidget(self)
        self.set_widget(custom_widget)
        
        # --- VARIABLES ---
        self.num_agents = 1     # updated dynamically when sim_data is provided
        self.current_R = np.eye(3)

        self.sim_data = None
        self.R_label = R_label

        # Static scene objects
        self.sphere = None

        self.context.robot_focus_changed.connect(self.update_axes_from_rotation)

    # ------------------------------------------------------------------
    # SCENE SETUP
    # ------------------------------------------------------------------
    def setup_scene(self):
        """Initialize the 3D attitude visualization scene."""
        self.set_background("white")
        self.show_bounds(grid=True, location="outer", color="black", xtitle="X", ytitle="Y", ztitle="Z")
        self.camera_position = "iso"
        self.camera.Azimuth(-80)
        self.camera.SetParallelProjection(False)
        self.enable_3_lights()

        # Add sphere grid and 3 attitude vectors (x, y, z axes)
        self._create_sphere_grid()
        self._create_axes_vectors()

        # Set a nice default view
        self.reset_camera()
        self.render()

    def reset_scene(self, sim_data=None, sim_settings=None):
        self.num_agents = sim_data[self.R_label].shape[1]

    # ------------------------------------------------------------------
    # AXES CREATION AND UPDATE
    # ------------------------------------------------------------------
    def _create_sphere_grid(self):
        """Create a reference sphere mesh."""
        mesh1 = create_sphere_grid(radius=1.0, lat_step=15, lon_step=15)
        mesh2 = create_sphere_grid(radius=1.0, lat_step=90, lon_step=None)
        geo_line1 = create_geodesic((-89.9,0), (90,0), radius=1.0, n_points=40)
        geo_line1_dashed = create_geodesic((-90.1,0), (90,0), radius=1.0, n_points=60)
        geo_line1_dashed = make_dashed_line(geo_line1_dashed, dash_length=3)
        geo_line2 = create_geodesic((-89.9,90), (90,90), radius=1.0, n_points=40)
        geo_line2_dashed = create_geodesic((-90.1,90), (90,90), radius=1.0, n_points=60)
        geo_line2_dashed = make_dashed_line(geo_line2_dashed, dash_length=2)

        kw_markers = {"line_width": 3}
        kw_markers_main = {"line_width": 6}
        self.add_mesh(mesh1, color="grey")
        self.add_mesh(mesh2, color="black", **kw_markers_main)
        self.add_mesh(geo_line1, color="black", **kw_markers_main)
        self.add_mesh(geo_line1_dashed, color="black", **kw_markers_main)
        self.add_mesh(geo_line2, color="black", **kw_markers)
        self.add_mesh(geo_line2_dashed, color="black", **kw_markers)

        self.sphere = pv.Sphere(radius=1.0, theta_resolution=30, phi_resolution=30)
        self.add_mesh(self.sphere, color="lightgray", opacity=0.05)

    def _create_axes_vectors(self):
        """Create initial x, y, z attitude vectors."""
        origin = np.array([0.0, 0.0, 0.0])
        axis_colors = {"x": "red", "y": "green", "z": "blue"}
        for i, (label, color) in enumerate(axis_colors.items()):
            end = origin + np.eye(3)[i]
            line = pv.Line(origin, end)
            self.add_scene_object(label, line, color=color, line_width=10, visible=False)

    def update_axes_from_rotation(self):
        """Update the attitude axes according to the given rotation matrix."""
        R = self.current_R[self.context.robot_focus, :, :]

        origin = np.array([0.0, 0.0, 0.0])
        axes = {"x": R[:, 0], "y": R[:, 1], "z": R[:, 2]}

        for label, vec in axes.items():
            mesh = self.scene_objects[label]["mesh"]
            mesh.points[0] = origin
            mesh.points[1] = vec
            mesh.Modified()
            self.scene_objects[label]["actor"].SetVisibility(True)

    # ------------------------------------------------------------------
    # DATA HANDLING
    # ------------------------------------------------------------------
    def update_all_scene_objects(self, sim_data, idx):
        """4
        Update attitude visualization from simulation data.

        sim_data[self.R_label] should have shape (T, N, 3, 3),
        where T = time steps, N = number of robots.
        """
        if self.R_label not in sim_data:
            raise KeyError(f"sim_data must contain '{self.R_label}' key for attitude visualization")

        self.current_R = sim_data[self.R_label][idx, :, :, :]
        self.update_axes_from_rotation()
        self.render()

    # ------------------------------------------------------------------
    # KEYBOARD CONTROL
    # ------------------------------------------------------------------
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Use PageUp/PageDown to switch between robots."""
        key = event.key()

        if key == QtCore.Qt.Key_Down:
            self.context.robot_focus = (self.context.robot_focus - 1) % self.num_agents
            self.label.setText(f"Robot idx: {self.context.robot_focus}")
            self.render()
        elif key == QtCore.Qt.Key_Up:
            self.context.robot_focus = (self.context.robot_focus + 1) % self.num_agents
            self.label.setText(f"Robot idx: {self.context.robot_focus}")
            self.render()
        elif key == QtCore.Qt.Key_R:
            self.reset_camera()
        event.accept()
