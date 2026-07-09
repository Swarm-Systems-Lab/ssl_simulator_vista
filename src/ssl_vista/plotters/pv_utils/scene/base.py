"""Foundational drawable model for the PyVista plotters.

Two building blocks live here:

``SceneObject``
    A single PyVista mesh + its VTK actor, carrying a rigid **pose**. Rigid motion
    is applied through ``actor.user_matrix`` (a 4x4 transform evaluated on the GPU),
    so moving a robot each frame costs a matrix assignment instead of a full NumPy
    recompute of ``mesh.points``. Objects whose geometry actually changes each frame
    (trajectories, glyph fields) update their points explicitly via ``update_mesh*``.

``SceneObjectGroup``
    An ordered collection of named children (``SceneObject`` or nested groups) that
    share a common frame. ``follow_pose`` children move rigidly with the group; other
    children (e.g. a world-frame trajectory tail) keep their own identity pose and are
    updated independently.

Both implement ``_attach(pvqt, name)``: the drawable creates its own actor(s) and
returns ``[(full_name, leaf_object), ...]`` for the plotter to register. This keeps
actor creation inside the drawable and lets a user supply a custom object (any
subclass of ``SceneObject``) without writing transformation code.
"""

__all__ = ["Drawable", "SceneObject", "SceneObjectGroup", "pose_matrix"]

from typing import Union

import numpy as np
import pyvista as pv

pv.global_theme.allow_empty_mesh = True


def pose_matrix(position=None, R=None, heading=None) -> np.ndarray:
    """Build a 4x4 homogeneous pose from any of position / rotation / heading.

    Parameters
    ----------
    position : array-like, optional
        Translation. Length 2 is padded with ``z = 0``.
    R : np.ndarray, optional
        3x3 rotation matrix. Ignored if ``heading`` is given.
    heading : float, optional
        Planar heading angle (radians) about +Z. Convenience for 2D objects.
    """
    M = np.eye(4)
    if heading is not None:
        c, s = np.cos(heading), np.sin(heading)
        R = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    if R is not None:
        M[:3, :3] = np.asarray(R, dtype=float)
    if position is not None:
        p = np.asarray(position, dtype=float).reshape(-1)
        if p.size == 2:
            p = np.array([p[0], p[1], 0.0])
        M[:3, 3] = p[:3]
    return M


class Drawable:
    """Interface for anything that can attach itself to a PyVista plotter."""

    def _attach(self, pvqt, name: str) -> list[tuple[str, "SceneObject"]]:
        """Create actor(s) on ``pvqt`` and return ``[(full_name, leaf_object), ...]``."""
        raise NotImplementedError

    def _set_world_pose(self, matrix: np.ndarray) -> None:
        """Set the object's world pose (used for group pose propagation)."""
        raise NotImplementedError

    # -- style / lifecycle broadcast interface (overridden by subclasses) --
    def set_pose(self, position=None, R=None, heading=None) -> None:
        self._set_world_pose(pose_matrix(position, R, heading))

    def set_color(self, color) -> None: ...
    def reset_color(self) -> None: ...
    def set_opacity(self, opacity: float) -> None: ...
    def set_visibility(self, visible: bool) -> None: ...
    def set_focus(self, focused: bool) -> None: ...


class SceneObject(Drawable):
    """A single mesh + actor with a rigid pose applied via ``actor.user_matrix``."""

    def __init__(self, mesh: pv.DataSet, *, pose: np.ndarray = None, size: float = 1.0, **style):
        self.mesh = mesh
        self.actor = None
        self.style = dict(style)
        self._visible = bool(self.style.pop("visible", True))
        self.default_color = None

        if size != 1.0:
            self._scale_reference(size)

        # ``local_pose`` is the object's offset within its parent group's frame;
        # ``_pose`` is its resolved world pose (what gets pushed to the actor).
        self.local_pose = np.eye(4) if pose is None else np.asarray(pose, dtype=float)
        self._pose = self.local_pose.copy()
        self.ref_centroid = np.asarray(self.mesh.center, dtype=float)

    def _scale_reference(self, size: float) -> None:
        center = np.asarray(self.mesh.center, dtype=float)
        self.mesh.points = (self.mesh.points - center) * size + center

    # ---------------------------------------------------------------
    # ATTACH / POSE
    # ---------------------------------------------------------------
    def _attach(self, pvqt, name: str) -> list[tuple[str, "SceneObject"]]:
        # ``visible`` is not an add_mesh kwarg; strip it (it may have been merged
        # into style after construction via SceneObjectGroup.add).
        style = dict(self.style)
        self._visible = bool(style.pop("visible", self._visible))
        self.actor = pvqt.add_mesh(self.mesh, **style)
        self.actor.user_matrix = self._pose
        self.actor.visibility = self._visible
        self.default_color = self.actor.prop.color
        return [(name, self)]

    def _set_world_pose(self, matrix: np.ndarray) -> None:
        self._pose = np.asarray(matrix, dtype=float) @ self.local_pose
        if self.actor is not None:
            self.actor.user_matrix = self._pose

    @property
    def world_center(self) -> np.ndarray:
        """Reference centroid mapped through the current pose (no point recompute)."""
        return self._pose[:3, :3] @ self.ref_centroid + self._pose[:3, 3]

    # ---------------------------------------------------------------
    # STYLE / VISIBILITY / FOCUS
    # ---------------------------------------------------------------
    def set_color(self, color: pv.ColorLike) -> None:
        if self.actor is not None:
            if self.default_color is None:
                self.default_color = self.actor.prop.color
            self.actor.prop.color = color

    def reset_color(self) -> None:
        if self.actor is not None and self.default_color is not None:
            self.actor.prop.color = self.default_color

    def set_opacity(self, opacity: float) -> None:
        if self.actor is not None:
            self.actor.prop.opacity = opacity

    def set_visibility(self, visible: bool) -> None:
        self._visible = bool(visible)
        if self.actor is not None:
            self.actor.visibility = self._visible

    def is_visible(self) -> bool:
        return self.actor.visibility if self.actor is not None else self._visible

    def set_focus(self, focused: bool) -> None:
        """Highlight (red) when focused; restore default color otherwise."""
        if focused:
            self.set_color("red")
        else:
            self.reset_color()

    # ---------------------------------------------------------------
    # DEFORMABLE GEOMETRY (mesh mutated in place; pose stays applied on top)
    # ---------------------------------------------------------------
    def update_mesh(self, new_mesh: pv.DataSet) -> None:
        """Swap the underlying mesh (topology may change)."""
        self.mesh = new_mesh
        if self.actor is not None:
            self.actor.mapper.dataset = new_mesh
            self.actor.mapper.Modified()

    def update_mesh_points(self, new_points: np.ndarray) -> None:
        """Update only the point coordinates (same point count)."""
        if self.mesh is not None and self.mesh.n_points == new_points.shape[0]:
            self.mesh.points = new_points
            self.mesh.Modified()
            if self.actor is not None:
                self.actor.mapper.Modified()


class SceneObjectGroup(Drawable):
    """An ordered set of named children sharing a common (rigid) frame."""

    def __init__(self):
        # name -> {"obj", "follow_pose", "recolor"}
        self.children: dict[str, dict] = {}
        self._pose = np.eye(4)

    # ---------------------------------------------------------------
    # COMPOSITION
    # ---------------------------------------------------------------
    def add(
        self,
        name: str,
        obj: Union[SceneObject, "SceneObjectGroup"],
        *,
        follow_pose: bool = True,
        recolor: bool = True,
        **style,
    ) -> None:
        """Add a child. ``follow_pose`` children move with the group's pose;
        ``recolor`` children participate in group-wide ``set_color``.

        Extra keyword arguments are merged into the child's render style.
        """
        if name in self.children:
            raise ValueError(f"Child '{name}' already exists in group")
        if style and isinstance(obj, SceneObject):
            obj.style.update(style)
        self.children[name] = {"obj": obj, "follow_pose": follow_pose, "recolor": recolor}

    def get(self, name: str) -> Union[SceneObject, "SceneObjectGroup"]:
        if name not in self.children:
            raise KeyError(f"Child '{name}' not found in group")
        return self.children[name]["obj"]

    # ---------------------------------------------------------------
    # ATTACH / POSE
    # ---------------------------------------------------------------
    def _attach(self, pvqt, prefix: str) -> list[tuple[str, SceneObject]]:
        registered: list[tuple[str, SceneObject]] = []
        for cname, rec in self.children.items():
            registered += rec["obj"]._attach(pvqt, f"{prefix}.{cname}")
        return registered

    def _set_world_pose(self, matrix: np.ndarray) -> None:
        self._pose = np.asarray(matrix, dtype=float)
        for rec in self.children.values():
            if rec["follow_pose"]:
                rec["obj"]._set_world_pose(self._pose)

    @property
    def world_center(self) -> np.ndarray:
        return self._pose[:3, 3].copy()

    # ---------------------------------------------------------------
    # STYLE / VISIBILITY / FOCUS (broadcast)
    # ---------------------------------------------------------------
    def set_color(self, color: pv.ColorLike) -> None:
        for rec in self.children.values():
            if rec["recolor"]:
                rec["obj"].set_color(color)

    def reset_color(self) -> None:
        for rec in self.children.values():
            if rec["recolor"]:
                rec["obj"].reset_color()

    def set_opacity(self, opacity: float) -> None:
        for rec in self.children.values():
            rec["obj"].set_opacity(opacity)

    def set_visibility(self, visible: bool) -> None:
        for rec in self.children.values():
            rec["obj"].set_visibility(visible)

    def set_focus(self, focused: bool) -> None:
        for rec in self.children.values():
            rec["obj"].set_focus(focused)

    # ---------------------------------------------------------------
    # CONTAINER PROTOCOL
    # ---------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.children)

    def __iter__(self):
        for name, rec in self.children.items():
            yield name, rec["obj"]

    def __getitem__(self, name: str) -> Union[SceneObject, "SceneObjectGroup"]:
        return self.get(name)
