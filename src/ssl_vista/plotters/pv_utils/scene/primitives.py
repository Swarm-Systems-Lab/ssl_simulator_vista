"""Concrete single-mesh scene primitives.

Rigid primitives (``Icon2D``, ``Icon3D``, ``Marker``, ``Mesh``) are posed via
``set_pose`` (GPU ``user_matrix``). Deformable primitives (``Line``, ``Trajectory``,
``StraightLine``, ``Vector``, ``VectorField``, ``PointCloud``) update their geometry
in place and are meant to hold world-frame coordinates.
"""

__all__ = [
    "Icon2D",
    "Icon3D",
    "Line",
    "Marker",
    "Mesh",
    "PointCloud",
    "StraightLine",
    "Trajectory",
    "Vector",
    "VectorField",
]

import numpy as np
import pyvista as pv

from ..factories import RobotFactory
from .base import SceneObject


class Mesh(SceneObject):
    """Explicit 'bring your own mesh' wrapper.

    Equivalent to :class:`SceneObject`, provided as a clearly named entry point
    for user-supplied geometry::

        obj = Mesh(pv.Sphere(), color="orange")
        plotter.add_scene_object("blob", obj)
        obj.set_pose(position=p, R=R)   # no transform code required
    """


class Icon2D(SceneObject):
    """A 2D robot icon (posed with a planar heading)."""

    def __init__(self, robot_type: str, **kwargs):
        mesh = RobotFactory(dimension=2).create(robot_type)
        super().__init__(mesh=mesh, **kwargs)


class Icon3D(SceneObject):
    """A 3D robot icon (posed with a 3x3 rotation)."""

    def __init__(self, robot_type: str, **kwargs):
        mesh = RobotFactory(dimension=3).create(robot_type)
        pts = np.asarray(mesh.points)
        if pts.shape[1] == 2:
            mesh.points = np.hstack([pts, np.zeros((pts.shape[0], 1))])
        super().__init__(mesh=mesh, **kwargs)


class Marker(SceneObject):
    """A small sphere marker at a pose (waypoints, targets, ...)."""

    def __init__(self, radius: float = 0.1, **kwargs):
        mesh = pv.Sphere(radius=radius, theta_resolution=20, phi_resolution=16)
        super().__init__(mesh=mesh, **kwargs)


class Line(SceneObject):
    """A world-frame polyline; call :meth:`set_points` to update it each frame."""

    def __init__(self, points=None, dashed: bool = False, dash_length: int = 5, **kwargs):
        self.dashed = dashed
        self.dash_length = dash_length

        if points is None:
            mesh = pv.PolyData()
            mesh.points = np.empty((0, 3))
            mesh.lines = np.empty((0,), dtype=np.int64)
        else:
            mesh = self._gen_line(points)

        super().__init__(mesh=mesh, **kwargs)

    def set_points(self, new_points: np.ndarray) -> None:
        self.update_mesh(self._gen_line(new_points))

    def _gen_line(self, points: np.ndarray) -> pv.PolyData:
        points = np.asarray(points, dtype=float)
        n_pts = points.shape[0]
        if points.ndim == 2 and points.shape[1] == 2:
            points = np.hstack([points, np.zeros((n_pts, 1))])

        mesh = pv.PolyData()
        mesh.points = points
        if n_pts < 2:
            mesh.lines = np.empty((0,), dtype=np.int64)
            return mesh

        conn = np.hstack([[2, i, i + 1] for i in range(n_pts - 1)]).astype(np.int64)
        mesh.lines = conn
        if self.dashed:
            from ..meshes import make_dashed_line

            return make_dashed_line(mesh, dash_length=self.dash_length)
        return mesh


class Trajectory(Line):
    """A :class:`Line` specialized for tails, with optional length trimming.

    ``max_len`` keeps only the most recent points, so consumers can pass the full
    position history and let the trajectory trim itself.
    """

    def __init__(self, points=None, max_len: int | None = None, **kwargs):
        self.max_len = max_len
        super().__init__(points=points, **kwargs)

    def set_points(self, new_points: np.ndarray) -> None:
        pts = np.asarray(new_points, dtype=float)
        if self.max_len is not None and pts.shape[0] > self.max_len:
            pts = pts[-self.max_len :]
        super().set_points(pts)


class StraightLine(SceneObject):
    """A fixed two-point segment (used as a rigid building block, e.g. axes)."""

    def __init__(self, start: np.ndarray, end: np.ndarray, **kwargs):
        super().__init__(mesh=pv.Line(start, end), **kwargs)


class Vector(SceneObject):
    """A single arrow (wrapper around ``pv.Arrow``)."""

    def __init__(self, origin: np.ndarray, direction: np.ndarray, scale: float = 1.0, **kwargs):
        self.scale = scale
        super().__init__(mesh=pv.Arrow(start=origin, direction=direction, scale=scale), **kwargs)

    def update_vector(self, origin: np.ndarray, direction: np.ndarray) -> None:
        self.update_mesh(pv.Arrow(start=origin, direction=direction, scale=self.scale))


class VectorField(SceneObject):
    """A glyph-based vector field: one mesh + one actor for many arrows.

    Suitable for hundreds-to-thousands of vectors at interactive frame rates.
    """

    def __init__(self, origins: np.ndarray, vectors: np.ndarray, scale: float = 1.0, **style):
        self.scale = scale
        self._template = pv.Arrow()
        self._poly = pv.PolyData(np.asarray(origins, dtype=float))
        self._set_vectors(vectors)
        super().__init__(mesh=self._glyph(), **style)

    def _set_vectors(self, vectors: np.ndarray) -> None:
        self._poly["vectors"] = np.asarray(vectors, dtype=float) * self.scale
        self._poly.set_active_vectors("vectors")

    def _glyph(self) -> pv.PolyData:
        return self._poly.glyph(orient="vectors", scale="vectors", factor=1.0, geom=self._template)

    def update_vectors(self, vectors: np.ndarray) -> None:
        self._set_vectors(vectors)
        self.mesh.shallow_copy(self._glyph())


class PointCloud(SceneObject):
    """A glyph-based point cloud (spheres); call :meth:`set_points` to update."""

    def __init__(self, points: np.ndarray, radius: float = 0.05, **style):
        self._template = pv.Sphere(radius=radius, theta_resolution=12, phi_resolution=10)
        self._poly = pv.PolyData(np.asarray(points, dtype=float))
        super().__init__(mesh=self._glyph(), **style)

    def _glyph(self) -> pv.PolyData:
        return self._poly.glyph(scale=False, orient=False, geom=self._template)

    def set_points(self, points: np.ndarray) -> None:
        self._poly.points = np.asarray(points, dtype=float)
        self.mesh.shallow_copy(self._glyph())
