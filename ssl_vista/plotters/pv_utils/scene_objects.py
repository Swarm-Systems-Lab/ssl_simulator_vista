__all__ = [
    "SceneObject",
    "Icon2D",
    "Icon3D",
    "Line",
    "StraightLine",
]

import numpy as np
import pyvista as pv

from .factories import RobotFactory

pv.global_theme.allow_empty_mesh = True

class SceneObject:
    def __init__(self, mesh: pv.MatrixLike, actor: pv.Actor = None):
        self.mesh = mesh
        self.actor = actor
        self.default_color = None
    
    def set_color(self, color: pv.ColorLike):
        if self.default_color is None:
            self.default_color = self.actor.prop.color
        if self.actor is not None:
            self.actor.prop.color = color

    def set_visibility(self, visible: bool):
        if self.actor is not None:
            self.actor.visibility = visible

# ------------------------------------------------------------------
# SPECIFIC SCENE OBJECTS
# ------------------------------------------------------------------

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

class Icon2D(SceneObject):
    def __init__(self, robot_type: str):
        self.robot_factory = RobotFactory(dimension=2)
        mesh_robot = self.robot_factory.create(robot_type)
        super().__init__(mesh=mesh_robot)
    
    def transform_to(
        self, 
        centroid: np.ndarray,     # (2,) target centroid
        orientation: float = None # scalar angle in radians
    ):
        # extract stored original points and centroid from field_data (factory should set these)
        original_points = np.asarray(self.mesh.field_data["orig_points"][:, :2])
        original_centroid = np.asarray(self.mesh.field_data["orig_centroid"][:2])

        # compute translation vector (target centroid - original centroid)
        translation = np.asarray(centroid) - original_centroid

        # apply transform (rotation R around orig_centroid then translation)
        new_points = transform_points(original_points, original_centroid, translation, orientation)
        self.mesh.points[:, :2] = new_points
        self.mesh.Modified()

class Icon3D(SceneObject):
    def __init__(self, robot_type: str):
        self.robot_factory = RobotFactory(dimension=3)
        mesh_robot = self.robot_factory.create(robot_type)

        # ensure mesh has 3D points (factory may give 2D -> ensure z column exists)
        pts = np.asarray(mesh_robot.points)
        if pts.shape[1] == 2:
            mesh_robot.points = np.hstack([pts, np.zeros((pts.shape[0], 1))])

        super().__init__(mesh=mesh_robot)

    def transform_to(
        self, 
        centroid: np.ndarray, # (3,) target centroid
        R: np.ndarray = None  # 3x3 rotation matrix
    ):
        # extract stored original points and centroid from field_data (factory should set these)
        # TODO: change it, stored by the SceneObject when created
        original_points = np.asarray(self.mesh.field_data["orig_points"])
        original_centroid = np.asarray(self.mesh.field_data["orig_centroid"])

        # compute translation vector (target centroid - original centroid)
        translation = np.asarray(centroid) - original_centroid

        # apply transform (rotation R around orig_centroid then translation)
        new_points = transform_points_3d(original_points, original_centroid, translation, R)
        self.mesh.points = new_points
        self.mesh.Modified()

class Line(SceneObject):
    def __init__(self):
        line = pv.PolyData()
        line.points = np.empty((0, 3))
        line.lines = np.empty((0,), dtype=int)
        super().__init__(mesh=line)
    
    def set_points(self, new_points: np.ndarray):
        n_pts = new_points.shape[0]
        if n_pts > 1:
            lines = np.hstack([[2, i, i + 1] for i in range(n_pts - 1)]).astype(np.int64)
        else:
            lines = np.empty((0,), dtype=np.int64)
        self.mesh.points = new_points
        self.mesh.lines = lines
        self.mesh.Modified()

class StraightLine(SceneObject):
    def __init__(self, start: np.ndarray, end: np.ndarray):
        line = pv.Line(start, end)
        super().__init__(mesh=line)
 