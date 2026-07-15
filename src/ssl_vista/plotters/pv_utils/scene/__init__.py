"""Scene-object model for the PyVista plotters.

Public API:

- Foundation: :class:`Drawable`, :class:`SceneObject`, :class:`SceneObjectGroup`,
  and the :func:`pose_matrix` helper.
- Primitives: :class:`Mesh`, :class:`Marker`, :class:`PointCloud`, :class:`Line`,
  :class:`Trajectory`, :class:`StraightLine`, :class:`Vector`, :class:`VectorField`,
  :class:`Label`, :class:`Icon2D`, :class:`Icon3D`.
- Composites: :class:`Axes`, :class:`Robot2D`, :class:`Robot3D`, :class:`Sphere`,
  :class:`SphereGrid`.
"""

from .base import Drawable, SceneObject, SceneObjectGroup, pose_matrix
from .composites import Axes, Robot2D, Robot3D, Sphere, SphereGrid
from .primitives import (
    ClippedSphere,
    Icon2D,
    Icon3D,
    Label,
    Line,
    Marker,
    Mesh,
    PointCloud,
    StraightLine,
    Trajectory,
    Vector,
    VectorField,
)

__all__ = [
    "Axes",
    "ClippedSphere",
    "Drawable",
    "Icon2D",
    "Icon3D",
    "Label",
    "Line",
    "Marker",
    "Mesh",
    "PointCloud",
    "Robot2D",
    "Robot3D",
    "SceneObject",
    "SceneObjectGroup",
    "Sphere",
    "SphereGrid",
    "StraightLine",
    "Trajectory",
    "Vector",
    "VectorField",
    "pose_matrix",
]
