"""Concrete single-mesh scene primitives.

Rigid primitives (``Icon2D``, ``Icon3D``, ``Marker``, ``Mesh``) are posed via
``set_pose`` (GPU ``user_matrix``). Deformable primitives (``Line``, ``Trajectory``,
``StraightLine``, ``Vector``, ``VectorField``, ``PointCloud``) update their geometry
in place and are meant to hold world-frame coordinates.
"""

__all__ = [
    "ClippedSphere",
    "Icon2D",
    "Icon3D",
    "Label",
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
from .base import Drawable, SceneObject


class Label(Drawable):
    """Billboard text anchored at fixed 3D points (via ``add_point_labels``).

    Screen-facing text that stays legible from any camera angle - used for static
    annotations such as axis labels. Not affected by ``set_pose``.
    """

    def __init__(self, points, labels, font_size: int = 18, text_color="black", **kwargs):
        self.points = np.atleast_2d(np.asarray(points, dtype=float))
        self.labels = [str(x) for x in labels]
        self.font_size = font_size
        self.text_color = text_color
        self._visible = bool(kwargs.pop("visible", True))
        self._kwargs = kwargs
        self.actor = None

    def _attach(self, pvqt, name: str):
        self.actor = pvqt.add_point_labels(
            self.points,
            self.labels,
            font_size=self.font_size,
            text_color=self.text_color,
            shape=None,
            show_points=False,
            always_visible=True,
            **self._kwargs,
        )
        self.actor.SetVisibility(self._visible)
        return [(name, self)]

    def _set_world_pose(self, matrix: np.ndarray) -> None:
        # Labels are anchored to fixed points; pose changes do not move them.
        pass

    def set_visibility(self, visible: bool) -> None:
        self._visible = bool(visible)
        if self.actor is not None:
            self.actor.SetVisibility(self._visible)


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
    """A fixed two-point segment (used as a rigid building block, e.g. axes).

    With ``tube_radius=None`` it renders as a ``pv.Line`` whose thickness is the
    screen-space ``line_width`` (constant in pixels, independent of zoom). Give a
    ``tube_radius`` to render it as a 3-D tube instead, so its thickness is in world
    units and scales with the camera like a mesh.
    """

    def __init__(
        self,
        start: np.ndarray,
        end: np.ndarray,
        tube_radius: float | None = None,
        tube_sides: int = 12,
        **kwargs,
    ):
        mesh = pv.Line(start, end)
        if tube_radius is not None:
            mesh = mesh.tube(radius=tube_radius, n_sides=tube_sides)
        super().__init__(mesh=mesh, **kwargs)


class Vector(SceneObject):
    """A single arrow (wrapper around ``pv.Arrow``).

    ``thickness`` scales the arrow's radial size (shaft + tip radius); the ``pv.Arrow``
    defaults are ``thickness=1.0``. ``tip_length`` / ``tip_radius`` / ``shaft_radius``
    can override the geometry directly (they take precedence over ``thickness``).
    """

    _SHAFT_RADIUS = 0.05  # pv.Arrow defaults, as a fraction of arrow length
    _TIP_RADIUS = 0.10

    def __init__(
        self,
        origin: np.ndarray,
        direction: np.ndarray,
        scale: float = 1.0,
        thickness: float = 1.0,
        tip_length: float = 0.25,
        tip_radius: float | None = None,
        shaft_radius: float | None = None,
        **kwargs,
    ):
        self.scale = scale
        self._arrow_kwargs = {
            "tip_length": tip_length,
            "tip_radius": self._TIP_RADIUS * thickness if tip_radius is None else tip_radius,
            "shaft_radius": self._SHAFT_RADIUS * thickness
            if shaft_radius is None
            else shaft_radius,
        }
        super().__init__(mesh=self._make_arrow(origin, direction), **kwargs)

    def _make_arrow(self, origin: np.ndarray, direction: np.ndarray) -> pv.PolyData:
        return pv.Arrow(start=origin, direction=direction, scale=self.scale, **self._arrow_kwargs)

    def update_vector(self, origin: np.ndarray, direction: np.ndarray) -> None:
        self.update_mesh(self._make_arrow(origin, direction))


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


class ClippedSphere(SceneObject):
    """A sphere shown only where it lies inside (or outside) a fixed clip sphere.

    Useful e.g. to draw a geodesic ball around a moving point on the SO(3) ball and
    keep only the portion within the manifold. The sphere is rebuilt and re-clipped
    each time its centre moves, so it is driven by :meth:`set_center` (deformable),
    not by ``set_pose`` (rigid).
    """

    def __init__(
        self,
        radius: float,
        clip_radius: float,
        clip_center=(0.0, 0.0, 0.0),
        center=(0.0, 0.0, 0.0),
        invert: bool = False,
        theta_resolution: int = 40,
        phi_resolution: int = 40,
        **style,
    ):
        self.radius = radius
        self.clip_radius = clip_radius
        self.clip_center = np.asarray(clip_center, dtype=float)
        self.invert = invert
        self._theta = theta_resolution
        self._phi = phi_resolution
        self._center = np.asarray(center, dtype=float).reshape(-1)[:3]
        super().__init__(mesh=self._build(self._center), **style)

    def _build(self, center: np.ndarray) -> pv.PolyData:
        from ..meshes import clip_inside_sphere

        sphere = pv.Sphere(
            radius=self.radius,
            center=center,
            theta_resolution=self._theta,
            phi_resolution=self._phi,
        )
        return clip_inside_sphere(
            sphere, self.clip_radius, center=self.clip_center, invert=self.invert
        )

    def set_center(self, center: np.ndarray) -> None:
        """Move the sphere's centre and re-clip against the fixed clip sphere."""
        self._center = np.asarray(center, dtype=float).reshape(-1)[:3]
        self.update_mesh(self._build(self._center))
