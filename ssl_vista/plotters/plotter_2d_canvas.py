__all__ = ["Plotter2DCanvas"]

import numpy as np
import pyvista as pv

from .plotter_canvas import BaseCanvasPlotter

class Plotter2DCanvas(BaseCanvasPlotter):
    """
    3D PyVista canvas for visualizing robots, trajectories, and vectors.
    """
    def __init__(
            self, 
            robot_type="unicycle", 
            robot_tail=500,
            robot_color="blue",
            label_pos="robot.p",
            label_heading="robot.theta",
            **kwargs):
        super().__init__(dimension=2, sim_data_labels=None, **kwargs)

        # - Robot parameters
        self.robot_type = robot_type
        self.robot_tail = robot_tail
        self.robot_color = robot_color

        # - Simulation data labels
        self.label_pos = label_pos
        self.label_heading = label_heading

        self.n_robots = 0
        self.robot_icons = []
        self.robot_trajs = []
        
    def init_artists(self, sim_data, sim_settings):
        """Initialize robots, trajectories, and vectors."""
        self._check_labels(sim_data)
        self._check_data_shapes(sim_data)

        # - Extract data for initialization
        data_pos = sim_data.get(self.label_pos)
        data_heading = sim_data.get(self.label_heading)

        if data_pos is None:
            raise ValueError(f"sim_data does not contain positions under '{self.label_pos}'")

        self.n_robots = data_pos.shape[1]

        # - Create robot meshes and trajectory placeholders
        base_name = "robot_"
        robots_kwargs = [{
            "name": f"{base_name}{i}", 
            "icon_type": self.robot_type, 
            "color": self.robot_color
        } for i in range(self.n_robots)]

        for i, robot_kwargs in enumerate(robots_kwargs):
            icon_name, traj_name = self.add_robot(**robot_kwargs)
            self.robot_icons.append(icon_name)
            self.robot_trajs.append(traj_name)
            self.scene_objects[icon_name].transform_to(
                centroid = data_pos[0, i, :],
                orientation = data_heading[0, i] if data_heading is not None else None
            )
        
    def update_artists(self, sim_data, idx):
        """
        Update positions and orientations for all robots and update their 3D trajectory tails.

        sim_data must contain positions under sim_data_labels['positions'] with shape (T,N,3).
        Optionally rotations under sim_data_labels['rotations'] with shape (T,N,3,3).
        """
        # - Extract data
        data_pos = sim_data.get(self.label_pos)
        data_heading = sim_data.get(self.label_heading)

        # - For each robot, update robot icon and trajectory meshes
        for i, icon_key in enumerate(self.robot_icons):
            icon_obj = self.scene_objects[icon_key]
            centroid = data_pos[idx, i, :]  # shape (2,)
            heading = data_heading[idx, i] if data_heading is not None else None

            icon_obj.transform_to(centroid, heading)
            icon_obj.set_visibility(True)

        for i, traj_key in enumerate(self.robot_trajs):
            traj_obj = self.scene_objects[traj_key]
            traj_xy = data_pos[0:idx, i, :] # shape (idx,2)
            traj_positions = np.hstack([traj_xy, np.zeros((traj_xy.shape[0], 1))])
            if self.robot_tail is not None and traj_positions.shape[0] > self.robot_tail:
                traj_positions = traj_positions[-self.robot_tail :, :]
            
            traj_obj.set_points(traj_positions)
            traj_obj.set_visibility(True)
        
        # - Update the canvas grid center
        new_center = np.array([data_pos[idx,...].mean(axis=0).tolist()])
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
        if self.label_heading is not None and self.label_heading not in sim_data:
            raise ValueError(f"sim_data must contain rotations at '{self.label_heading}'")

    def _check_data_shapes(self, sim_data):
        """Ensure data shapes are correct."""
        data_pos = sim_data.get(self.label_pos)
        if data_pos.ndim != 3 or data_pos.shape[2] != 2:
            raise ValueError(f"Positions array must be shape (T,N,2), got {data_pos.shape}")
        data_heading = sim_data.get(self.label_heading)
        if data_heading is not None:
            if data_heading.ndim != 2 or data_heading.shape[1] != data_pos.shape[1]:
                raise ValueError(f"Heading array must be shape (T,N={data_pos.shape[1]}), got {data_heading.shape}")