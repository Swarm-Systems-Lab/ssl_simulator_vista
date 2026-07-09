"""Scene-object model for the PyVista plotters.

Public API:

- Foundation: :class:`Drawable`, :class:`SceneObject`, :class:`SceneObjectGroup`,
  and the :func:`pose_matrix` helper.
- Primitives: :class:`Mesh`, :class:`Marker`, :class:`PointCloud`, :class:`Line`,
  :class:`Trajectory`, :class:`StraightLine`, :class:`Vector`, :class:`VectorField`,
  :class:`Icon2D`, :class:`Icon3D`.
- Composites: :class:`Axes`, :class:`Robot2D`, :class:`Robot3D`, :class:`SphereGrid`.
"""

from .base import Drawable, SceneObject, SceneObjectGroup, pose_matrix
from .composites import Axes, Robot2D, Robot3D, SphereGrid
from .primitives import (
    Icon2D,
    Icon3D,
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
    "Drawable",
    "Icon2D",
    "Icon3D",
    "Line",
    "Marker",
    "Mesh",
    "PointCloud",
    "Robot2D",
    "Robot3D",
    "SceneObject",
    "SceneObjectGroup",
    "SphereGrid",
    "StraightLine",
    "Trajectory",
    "Vector",
    "VectorField",
    "pose_matrix",
]
