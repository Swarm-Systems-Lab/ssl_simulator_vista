__all__ = ["Plotter2DCanvas"]

import sys
import numpy as np
import pyvista as pv

from ssl_vista.config import CONFIG

from ._base_plotters import BaseVisualPlotter
from .factories import RobotFactory

pv.global_theme.allow_empty_mesh = True


def transform_points(points, centroid, translation, orientation=None):
    pts = points.copy()
    if orientation is not None:
        R = np.array([
            [np.cos(orientation), -np.sin(orientation)],
            [np.sin(orientation), np.cos(orientation)]
        ])
        pts = (R @ (pts - centroid).T).T + centroid
    pts += translation
    return pts

class Plotter2DCanvas(BaseVisualPlotter):   
    """Custom QtInteractor that ignores all keyboard input."""

    def __init__(
            self, 
            parent=None, 
            sim_data_labels=None, 
            robot_type="default", 
            robot_tail=100, 
            color="blue",
            grid_range=[10,10], 
            grid_ticks=[11,11], 
            **kwargs
    ):
        super().__init__(parent=parent, **kwargs)
        self.robot_grid_mesh = None
        self.robot_grid_center = np.array([0.0, 0.0, 0.0])
        self.robot_grid_ticks = grid_ticks
        self.robot_grid_range = grid_range
        self.robot_factory = RobotFactory()

        if sim_data_labels is None:
            sim_data_labels = {"positions": "robot.p", "orientations": "robot.theta"}
        self.sim_data_labels = sim_data_labels

        self.robot_type = robot_type
        self.robot_tail = robot_tail
        self.default_color = color

    # ---------------------------------------------------------------
    # SCENE SETUP
    # ---------------------------------------------------------------
    def setup_scene(self):
        self.set_background("white")
        self.camera_position = "xy"
        self.camera.SetParallelProjection(True)
        self.enable_2d_style()

        # Add a reference grid
        range_x, range_y = self.robot_grid_range
        ticks_x, ticks_y = self.robot_grid_ticks
        self.robot_grid_mesh = pv.Plane(i_size=range_x, j_size=range_y, i_resolution=2, j_resolution=2)  # TODO: adapt size
        self.add_mesh(self.robot_grid_mesh, color="lightgray", style="wireframe", opacity=0.0)
        self.show_bounds(grid=True, location="all", color="black", xtitle="X", ytitle="Y", 
                         minor_ticks=True, n_xlabels=ticks_x, n_ylabels=ticks_y)
        self.reset_camera()

        # self.add_observer("RenderEvent", self.update_robot_grid)
        # self.add_observer("InteractionEvent", self.on_camera_move)

    def update_robot_grid(self):
        # Translate the robot grid mesh points
        translation = self.robot_grid_center - self.robot_grid_mesh.center
        self.robot_grid_mesh.points += translation
        self.update_bounds_axes()

    def reset_scene(self, sim_data=None, sim_settings=None):
        """
        Reset the scene by removing all robots and adding new ones based on the simulation data.
        """
        # Remove all robots from the scene
        robot_names = [name for name in self.scene_objects.keys() if ".traj" not in name]
        for name in robot_names:
            self.remove_scene_object(name)
            self.remove_scene_object(f"{name}.traj")

        # Add new robots based on the shape of sim_data["positions"]
        if sim_data is not None:
            pos_label = self.sim_data_labels.get("positions")
            positions = sim_data.get(pos_label)
            if positions is None:
                raise ValueError(f"sim_data does not contain positions under '{pos_label}'")
            
            n_robots = positions.shape[1]

            # Robot color can be specified on sim_data, otherwise use default
            self.add_multiple_robots(count=n_robots, base_name="robot_", robot_type=self.robot_type)
        
        self.print_scene_objects()

    # ---------------------------------------------------------------
    # SCENE MANAGEMENT
    # ---------------------------------------------------------------
    def add_multiple_robots(self, count, base_name, robot_type, color=None):
        if color is None:
            color = self.default_color
        robots = [
            {"name": f"{base_name}{i}", "type": robot_type, "color": color}
            for i in range(count)
        ]
        self.add_robots(robots)

    def add_robots(self, robots):
        """Add robots and optional trajectory meshes."""
        for robot in robots:
            name = robot["name"]
            mesh_robot = self.robot_factory.create(robot["type"])
            self.add_scene_object(name, mesh_robot, color=robot["color"], visible=False)

            # Trajectory mesh
            pv.global_theme.allow_empty_mesh = True
            mesh_traj = pv.PolyData()
            mesh_traj.points = np.empty((0, 3))
            mesh_traj.lines = np.empty((0,), dtype=int)
            self.add_scene_object(f"{name}.traj", mesh_traj, color=robot["color"], line_width=1)

    # ---------------------------------------------------------------
    # UPDATE SCENE OBJECTS
    # ---------------------------------------------------------------
    def update_all_scene_objects(self, sim_data, idx):
        """
        Update all scene objects using the specified labels from sim_data.

        Parameters
        ----------
        sim_data : dict
            Dictionary containing simulation data arrays.
        idx : int
            Current timestep index.
        """
        # Extract positions
        pos_label = self.sim_data_labels.get("positions")
        positions_data = sim_data.get(pos_label)
        if positions_data is None:
            raise ValueError(f"sim_data does not contain positions under '{pos_label}'")
        positions = positions_data[idx, :, :]  # shape (n_robots, 2)

        # Extract orientations if provided
        orient_label = self.sim_data_labels.get("orientations")
        orientations = sim_data.get(orient_label)
        if orientations is not None:
            orientations = orientations[idx, :]  # shape (n_robots,)
        
        # Check consistency
        n_robots = len([k for k in self.scene_objects if ".traj" not in k])
        if positions.shape[0] != n_robots:
            raise ValueError(f"Number of positions ({positions.shape[0]}) does not match number of robots ({n_robots}).")

        # Update each robot
        counter = 0
        for name, obj in self.scene_objects.items():
            if ".traj" in name:
                # Update trajectory tail
                traj_xy = positions_data[0:idx, counter, :]
                new_points = np.hstack([traj_xy, np.zeros((traj_xy.shape[0], 1))])
                
                # Keep only last robot_tail points
                if self.robot_tail is not None and new_points.shape[0] > self.robot_tail:
                    new_points = new_points[-self.robot_tail:, :]

                # Update lines connectivity
                n_pts = new_points.shape[0]
                if n_pts > 1:
                    # Each segment: [2, i, i+1]
                    lines = np.hstack([[2, i, i + 1] for i in range(n_pts - 1)])
                else:
                    lines = np.empty((0,), dtype=int)

                # Assign to mesh
                obj["mesh"].points = new_points
                obj["mesh"].lines = lines
                obj["actor"].visibility = True
                counter += 1
                
            else:
                # Update robot position and orientation
                centroid = positions[counter]
                orientation = orientations[counter] if orientations is not None else None
                self._update_robot(name, centroid, orientation)

        # Final render
        self.robot_grid_center = np.array([positions.mean(axis=0).tolist() + [0.0]])
        self.update_robot_grid()
        self.render()

            
    def _update_robot(self, name, centroid, orientation=None):
        if name not in self.scene_objects:
            raise ValueError(f"Object '{name}' not found in the scene.")

        obj_mesh = self.scene_objects[name]["mesh"]
        obj_actor = self.scene_objects[name]["actor"]
        obj_actor.visibility = True

        if not isinstance(obj_mesh, pv.PolyData):
            raise TypeError(f"Scene object '{name}' is not a PolyData object.")

        # Translate and rotate
        orig_points = obj_mesh.field_data["orig_points"][:, :2]
        current_centroid = obj_mesh.field_data["orig_centroid"][:2]
        translation = np.array(centroid) - current_centroid
        obj_mesh.points[:, :2] = transform_points(orig_points, current_centroid, translation, orientation)