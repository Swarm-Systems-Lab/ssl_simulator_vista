__all__ = ["Plotter3DCanvas"]

import numpy as np
import pyvista as pv

from ._base_py_plotter import BaseVisualPlotter
from .factories import RobotFactory

pv.global_theme.allow_empty_mesh = True


def transform_points_3d(points, centroid, translation, R=None):
    """
    Apply 3D rotation (R) around centroid and then translation.
    - points: (M,3) array of original points
    - centroid: (3,) original centroid
    - translation: (3,) translation vector to apply after rotation
    - R: (3,3) rotation matrix, or None to skip rotation
    Returns transformed points (M,3)
    """
    pts = points.copy()
    if R is not None:
        R = np.asarray(R, dtype=float)
        # subtract centroid, rotate, add centroid back
        pts = (R @ (pts - centroid).T).T + centroid
    pts += np.asarray(translation, dtype=float)
    return pts


class Plotter3DCanvas(BaseVisualPlotter):
    """
    3D PyVista canvas for spatial visualization of robots + trajectories.

    Expects sim_data to contain:
      - positions: sim_data[ sim_data_labels['positions'] ] shape (T, N, 3)
      - optionally rotations: sim_data[ sim_data_labels['rotations'] ] shape (T, N, 3, 3)
    """

    def __init__(
        self,
        parent=None,
        sim_data_labels=None,
        robot_type="default",
        robot_tail=100,
        color="blue",
        **kwargs
    ):
        super().__init__(parent=parent, **kwargs)
        self.robot_factory = RobotFactory(dimension=3)
        if sim_data_labels is None:
            sim_data_labels = {"positions": "robot.p", "rotations": "robot.R"}
        self.sim_data_labels = sim_data_labels

        self.robot_type = robot_type
        self.robot_tail = robot_tail
        self.default_color = color

    # -------------------------
    # Scene setup / reset
    # -------------------------
    def setup_scene(self):
        """Setup a 3D scene: iso camera, lighting, optional reference sphere."""
        self.set_background("white")
        self.show_bounds(grid=True, location="outer", color="black", xtitle="X", ytitle="Y", ztitle="Z")
        self.camera_position = "iso"
        self.camera.Azimuth(-90)
        self.camera.SetParallelProjection(False)
        self.enable_3_lights()

        self.reset_camera()

    def reset_scene(self, sim_data=None, sim_settings=None):
        """
        Remove existing robot objects and re-create them according to sim_data shape.
        """
        # remove robot meshes and trajectories
        robot_names = [n for n in list(self.scene_objects.keys()) if not n.endswith(".traj")]
        for name in robot_names:
            self.remove_scene_object(name)
            self.remove_scene_object(f"{name}.traj")

        # create robots if sim_data provided
        if sim_data is not None:
            pos_label = self.sim_data_labels.get("positions")
            positions = sim_data.get(pos_label)
            if positions is None:
                raise ValueError(f"sim_data does not contain positions under '{pos_label}'")
            # positions shape: (T, N, 3)
            n_robots = positions.shape[1]
            self.add_multiple_robots(count=n_robots, base_name="robot_", robot_type=self.robot_type, color=self.default_color)
        
        self.print_scene_objects()

    # -------------------------
    # Adding robots
    # -------------------------
    def add_multiple_robots(self, count, base_name, robot_type, color=None):
        if color is None:
            color = self.default_color
        robots = [{"name": f"{base_name}{i}", "type": robot_type, "color": color} for i in range(count)]
        self.add_robots(robots)
        self.reset_camera()

    def add_robots(self, robots):
        """
        Add robot meshes and their trajectory placeholders.
        Robot meshes created by RobotFactory should supply field_data orig_points (M,3) and orig_centroid (3,).
        """
        for robot in robots:
            name = robot["name"]
            mesh_robot = self.robot_factory.create(robot["type"])
            # Ensure mesh has 3D points (factory may give 2D -> ensure z column exists)
            pts = np.asarray(mesh_robot.points)
            if pts.shape[1] == 2:
                mesh_robot.points = np.hstack([pts, np.zeros((pts.shape[0], 1))])
            # Add robot invisibly by default
            self.add_scene_object(name, mesh_robot, color=robot.get("color", self.default_color), visible=False)

            # Trajectory placeholder (empty)
            pv.global_theme.allow_empty_mesh = True
            mesh_traj = pv.PolyData()
            mesh_traj.points = np.empty((0, 3))
            mesh_traj.lines = np.empty((0,), dtype=int)
            self.add_scene_object(f"{name}.traj", mesh_traj, color=robot.get("color", self.default_color), line_width=2, visible=False)

    # -------------------------
    # Updates from sim_data
    # -------------------------
    def update_all_scene_objects(self, sim_data, idx):
        """
        Update positions and orientations for all robots and update their 3D trajectory tails.

        sim_data must contain positions under sim_data_labels['positions'] with shape (T,N,3).
        Optionally rotations under sim_data_labels['rotations'] with shape (T,N,3,3).
        """
        pos_label = self.sim_data_labels.get("positions")
        positions_data = sim_data.get(pos_label)
        if positions_data is None:
            raise ValueError(f"sim_data must contain positions at '{pos_label}'")

        if positions_data.ndim != 3 or positions_data.shape[2] != 3:
            raise ValueError(f"Positions array must be shape (T,N,3), got {positions_data.shape}")

        # optional rotations
        rot_label = self.sim_data_labels.get("rotations")
        rotations_data = sim_data.get(rot_label, None)
        if rotations_data is not None:
            if rotations_data.ndim != 4 or rotations_data.shape[2:] != (3, 3):
                raise ValueError(f"Rotations array must be shape (T,N,3,3) if provided, got {rotations_data.shape}")

        # number of robots from scene objects
        n_scene_robots = len([k for k in self.scene_objects if not k.endswith(".traj")])
        n_positions = positions_data.shape[1]
        if n_scene_robots != n_positions:
            # allow reset_scene to be called by caller to sync; else raise
            raise ValueError(f"Scene has {n_scene_robots} robots but sim_data provides {n_positions}")

        # For each object, either trajectory or robot update
        counter = 0
        for name, obj in self.scene_objects.items():
            if name.endswith(".traj"):
                # build trajectory from t=0..idx-1 for that robot index
                traj_positions = positions_data[0:idx, counter, :]  # shape (idx,3)
                if traj_positions.size == 0:
                    new_points = np.empty((0, 3))
                else:
                    new_points = np.asarray(traj_positions, dtype=float)
                # keep tail length
                if self.robot_tail is not None and new_points.shape[0] > self.robot_tail:
                    new_points = new_points[-self.robot_tail :, :]
                # line connectivity
                n_pts = new_points.shape[0]
                if n_pts > 1:
                    # create connectivity array: [2, i, i+1, 2, i+1, i+2, ...]
                    lines = np.hstack([[2, i, i + 1] for i in range(n_pts - 1)]).astype(np.int64)
                else:
                    lines = np.empty((0,), dtype=np.int64)
                # assign
                obj["mesh"].points = new_points
                obj["mesh"].lines = lines
                obj["actor"].visibility = True
                counter += 1

            else:
                # robot mesh update: rotation + translation
                centroid3 = positions_data[idx, counter, :]  # (3,)
                if rotations_data is not None:
                    R = rotations_data[idx, counter, :, :]
                else:
                    R = None
                self._update_robot_3d(obj, centroid3, R)
                obj["actor"].visibility = True
                
        # Final render
        self.render()

    # -------------------------
    # Low-level robot update
    # -------------------------
    def _update_robot_3d(self, obj, centroid3, R=None):
        """
        Apply rotation (3x3) and translation to the robot mesh stored in scene_objects[name].
        centroid3: (3,) absolute position where the robot centroid should be after transform.
        R: (3,3) rotation matrix in world coordinates (applied about orig_centroid). If None, only translate.
        """

        mesh = obj["mesh"]

        if not isinstance(mesh, pv.PolyData):
            raise TypeError(f"Scene object '{obj}' is not a PolyData object.")

        # Extract stored original points and centroid from field_data (factory should set these)
        orig_points = np.asarray(mesh.field_data["orig_points"])
        orig_centroid = np.asarray(mesh.field_data["orig_centroid"])

        # compute translation vector (target centroid - original centroid)
        translation = np.asarray(centroid3) - orig_centroid

        # apply transform (rotation R around orig_centroid then translation)
        new_pts = transform_points_3d(orig_points, orig_centroid, translation, R)
        mesh.points = new_pts