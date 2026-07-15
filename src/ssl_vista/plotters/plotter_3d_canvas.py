__all__ = ["Plotter3DCanvas"]

import numpy as np
import pyvista as pv

from .base_canvas import BaseCanvasPlotter
from .pv_utils.configs import RobotConfig

_ROBOT_DEFAULTS = {"type": "unicycle", "color": "darkgrey", "size": 0.5, "tail": 500, "axes": True}


class Plotter3DCanvas(BaseCanvasPlotter):
    """
    3D PyVista canvas for visualizing robots, trajectories, and vectors.
    """

    def __init__(
        self,
        *,
        robot=None,
        grid=None,
        camera=None,
        graphics=None,
        label_pos="robot.p",
        label_rot="robot.R",
        parent=None,
        context=None,
    ):
        robot_cfg = RobotConfig.resolve(robot, defaults=_ROBOT_DEFAULTS)
        super().__init__(
            dimension=3,
            parent=parent,
            context=context,
            grid=grid,
            camera=camera,
            graphics=graphics,
            robot=robot_cfg,
        )

        # - Robot parameters (kept as attributes for init_artists/update_artists)
        self.robot_type = self.robot_config.type
        self.robot_tail = self.robot_config.tail
        self.robot_color = self.robot_config.color
        self.robot_size = self.robot_config.size
        self.robot_axes = self.robot_config.axes

        # - Simulation data labels
        self.label_pos = label_pos
        self.label_rot = label_rot

        self.robot_objs = []

    # ------------------------------------------------------------------
    # INIT ARTISTS
    # ------------------------------------------------------------------
    def init_artists(self, sim_data, sim_settings):
        """Initialize robots, trajectories, and vectors."""
        self.robot_objs.clear()
        self._check_labels(sim_data)
        self._check_data_shapes(sim_data)

        # - Extract data for initialization
        data_pos = sim_data.get(self.label_pos)
        data_rot = sim_data.get(self.label_rot)

        if data_pos is None:
            raise ValueError(f"sim_data does not contain positions under '{self.label_pos}'")

        n_robots = data_pos.shape[1]

        # - Create robot meshes and trajectory placeholders
        base_name = "robot_"
        robots_kwargs = [
            {
                "robot_name": f"{base_name}{i}",
                "icon_type": self.robot_type,
                "color": self.robot_color,
                "size": self.robot_size,
                "axes": self.robot_axes,
                "traj_max_len": self.robot_tail,
            }
            for i in range(n_robots)
        ]

        for i, robot_kwargs in enumerate(robots_kwargs):
            obj_robot = self.add_robot(**robot_kwargs)
            self.robot_objs.append(obj_robot)
            obj_robot.set_pose(
                position=data_pos[0, i, :], R=data_rot[0, i, :, :] if data_rot is not None else None
            )

    # ------------------------------------------------------------------
    # UPDATE ARTISTS
    # ------------------------------------------------------------------
    def update_artists(self, sim_data, idx):
        """
        Update positions and orientations for all robots and update their 3D trajectory tails.

        sim_data must contain positions under sim_data_labels['positions'] with shape (T,N,3).
        Optionally rotations under sim_data_labels['rotations'] with shape (T,N,3,3).
        """
        # - Extract data
        data_pos = sim_data.get(self.label_pos)
        data_rot = sim_data.get(self.label_rot)

        # - For each robot, update robot icon and trajectory meshes
        for i, robot_obj in enumerate(self.robot_objs):
            centroid3 = data_pos[idx, i, :]  # shape (3,)
            R = data_rot[idx, i, :, :] if data_rot is not None else None
            robot_obj.set_pose(position=centroid3, R=R)

            # Full history; the trajectory trims itself to traj_max_len.
            robot_obj.set_traj_points(data_pos[0:idx, i, :])
            robot_obj.set_visibility(True)

        # - Update the canvas grid center
        new_center = np.array([data_pos[idx, ...].mean(axis=0).tolist()])
        self.set_grid_centroid(new_center)

    # def when_change_robot_focus(self, new_focus, prev_focus):
    #     """Handle robot focus change."""
    #     print("Changed robot focus from", prev_focus, "to", new_focus)

    # ---------------------------------------------------------------
    # SANITY CHECKS
    # ---------------------------------------------------------------
    def _check_labels(self, sim_data):
        """Ensure required labels are in sim_data."""
        if self.label_pos not in sim_data:
            raise ValueError(f"sim_data must contain positions at '{self.label_pos}'")
        if self.label_rot is not None and self.label_rot not in sim_data:
            raise ValueError(f"sim_data must contain rotations at '{self.label_rot}'")

    def _check_data_shapes(self, sim_data):
        """Ensure data shapes are correct."""
        data_pos = sim_data.get(self.label_pos)
        if data_pos.ndim != 3 or data_pos.shape[2] != 3:
            raise ValueError(f"Positions array must be shape (T,N,3), got {data_pos.shape}")
        data_rot = sim_data.get(self.label_rot)
        if data_rot is not None and (data_rot.ndim != 4 or data_rot.shape[2:] != (3, 3)):
            raise ValueError(f"Rotations array must be shape (T,N,3,3), got {data_rot.shape}")
