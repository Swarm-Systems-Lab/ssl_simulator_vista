__all__ = ["Plotter3DAttitude"]

import numpy as np
import pyvista as pv
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QLabel, QPushButton, QToolBar, QVBoxLayout, QWidget
from ssl_simulator.math import check_and_parse_dimensions

from ._base_plotters import _BaseVisualPlotter
from .base_canvas import apply_camera
from .pv_utils.configs import CameraConfig
from .pv_utils.scene import Axes, SphereGrid


class Plotter3DAttitude(_BaseVisualPlotter):
    """3D Attitude visualizer for a single robot's orientation matrix."""

    def __init__(
        self,
        *,
        parent=None,
        context=None,
        label_rot="R",
        camera=None,
        tails=True,
        tail_max_len=None,
        initial_ghost=True,
    ):
        super().__init__(parent=parent, context=context)

        # - Tail / ghost options
        self.show_tails = tails
        self.tail_max_len = tail_max_len
        self.show_initial = initial_ghost

        if self.context.robot_focus is None:
            self.context.robot_focus = 0
        else:  # FIXME: better focus implementation
            custom_widget = QWidget(parent)
            layout = QVBoxLayout(custom_widget)

            # Add a toolbar at the top
            toolbar = QToolBar(custom_widget)
            layout.addWidget(toolbar)

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

        # - Camera (attitude default: iso view, azimuth -80). The reference frame is
        #   the spherical SphereGrid, not the box CanvasGrid.
        self.camera_config = CameraConfig.build(camera, azimuth=-80)

        # - Scene objects: rotating body axes + the fixed spherical reference grid
        self.obj_axes = None
        self.obj_axes_init = None  # faded ghost of the initial orientation
        self.obj_sphere = None
        self._data_rot = None  # cached history for tails / ghost on focus change
        self._idx = 0

        # - Connect to context signals
        self.context.robot_focus_changed.connect(self._rotate_axes)

    # ------------------------------------------------------------------
    # SCENE SETUP
    # ------------------------------------------------------------------
    def setup_scene(self):
        """Set up the camera and lighting (the spherical grid is built in init_artists)."""
        apply_camera(self.pvqt, self.camera_config.resolved(3))

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
        focus = min(self.context.robot_focus or 0, self.num_agents - 1)

        self.obj_axes = Axes(
            tube_radius=0.02, tails=self.show_tails, tail_max_len=self.tail_max_len, tail_width=4
        )
        self.obj_sphere = SphereGrid(axis_colors=("black", "black", "black"), lw=1.4)
        self.add_scene_object("axes", self.obj_axes)
        self.add_scene_object("sphere_grid", self.obj_sphere)

        # Faded ghost of the initial orientation
        if self.show_initial:
            self.obj_axes_init = Axes(tube_radius=0.02)
            self.add_scene_object("axes_init", self.obj_axes_init)
            self.obj_axes_init.set_pose(R=data_rot[0, focus])
            self.obj_axes_init.set_opacity(0.2)

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
        self._data_rot = data_rot
        self._idx = idx
        self._rotate_axes()

    # ------------------------------------------------------------------
    # DATA HANDLING
    # ------------------------------------------------------------------
    def _rotate_axes(self):
        """Rotate the body axes to the current orientation and refresh tails/ghost."""
        if self.obj_axes is None:
            return
        focus = min(self.context.robot_focus or 0, self.num_agents - 1)
        self.obj_axes.set_pose(R=self.current_R[focus, :, :])
        self._update_tails_and_ghost(focus)

    def _update_tails_and_ghost(self, focus: int) -> None:
        """Feed the axis tip tails and place the initial-orientation ghost."""
        if self._data_rot is None:
            return
        if self.obj_axes is not None and self.obj_axes.tails:
            # include the current frame so the tails reach the live axis tips
            self.obj_axes.set_tail_points(self._data_rot[: self._idx + 1, focus])
        if self.obj_axes_init is not None:
            self.obj_axes_init.set_pose(R=self._data_rot[0, focus])

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
