"""Composite scene objects built from primitives (grouped, rigid where relevant)."""

__all__ = ["Axes", "Robot2D", "Robot3D", "Sphere", "SphereGrid"]

import numpy as np
import pyvista as pv

from ..configs import DEFAULT_GRAPHICS, GraphicsConfig
from .base import SceneObject, SceneObjectGroup
from .primitives import Icon2D, Icon3D, Label, StraightLine, Trajectory, Vector


class Axes(SceneObjectGroup):
    """The x/y/z attitude axes as a rigid group (posed via ``set_pose``).

    By default the axes are screen-space lines (``line_width``, constant in pixels).
    Pass ``tube_radius`` to render them as world-space tubes instead, so their
    thickness scales with the camera like the rest of the scene.

    With ``tails=True`` each axis also gets a world-frame trajectory (in the axis'
    colour) tracing the path of its tip over time - fed via :meth:`set_tail_points`.
    """

    def __init__(
        self,
        size: float = 1.0,
        axis_colors=None,
        graphics: GraphicsConfig = DEFAULT_GRAPHICS,
        tube_radius: float | None = None,
        tube_sides: int = 12,
        tails: bool = False,
        tail_max_len: int | None = None,
        tail_width: float | None = None,
        **kwargs,
    ):
        super().__init__()
        if axis_colors is None:
            axis_colors = {"x": "red", "y": "green", "z": "blue"}
        self.size = size

        kwargs.setdefault("line_width", graphics.axes_line_width * size)
        line_length = kwargs.pop("line_length", size)
        # tube_radius is in world units; scale with `size` so it stays proportional.
        radius = None if tube_radius is None else tube_radius * size

        origin = np.zeros(3)
        for i, (label, color) in enumerate(axis_colors.items()):
            end = origin + line_length * np.eye(3)[i]
            line = StraightLine(origin, end, tube_radius=radius, tube_sides=tube_sides)
            # recolor=False keeps each axis its own color when a parent recolors.
            self.add(label, line, recolor=False, color=color, **kwargs)

        # Optional per-axis tip tails (world-frame, so they do NOT follow the pose).
        self.tails = {}
        if tails:
            tw = graphics.trajectory_size if tail_width is None else tail_width
            for label, color in axis_colors.items():
                traj = Trajectory(max_len=tail_max_len)
                self.add(
                    f"{label}_tail",
                    traj,
                    follow_pose=False,
                    recolor=False,
                    color=color,
                    line_width=tw,
                )
                self.tails[label] = traj

    def set_tail_points(self, R_history) -> None:
        """Update the axis tip tails from a rotation history ``(K, 3, 3)``.

        Each axis tail traces its tip ``R(t) · (size · e_i)`` - a path on the sphere
        of radius ``size``. No-op when the axes were built without ``tails=True``.
        """
        if not self.tails:
            return
        R_history = np.asarray(R_history, dtype=float)
        for i, traj in enumerate(self.tails.values()):
            if R_history.size == 0:
                traj.set_points(np.empty((0, 3)))
            else:
                traj.set_points(R_history @ (self.size * np.eye(3)[i]))


class Robot2D(SceneObjectGroup):
    """A 2D robot: rigid icon + world-frame trajectory tail."""

    def __init__(
        self,
        robot_type: str = "default",
        size: float = 1.0,
        traj_max_len=None,
        graphics: GraphicsConfig = DEFAULT_GRAPHICS,
        **kwargs,
    ):
        super().__init__()
        self.icon = Icon2D(robot_type=robot_type, size=size)
        self.traj = Trajectory(max_len=traj_max_len)

        # A caller-supplied line_width applies to the trajectory (icons are faces).
        traj_lw = kwargs.pop("line_width", graphics.trajectory_size * size)
        self.add("trajectory", self.traj, follow_pose=False, line_width=traj_lw, **kwargs)
        self.add("icon", self.icon, **kwargs)

    def set_traj_points(self, new_points: np.ndarray) -> None:
        self.traj.set_points(new_points)


class Robot3D(SceneObjectGroup):
    """A 3D robot: rigid icon (+ optional axes) + world-frame trajectory tail."""

    def __init__(
        self,
        robot_type: str = "default",
        axes: bool = True,
        size: float = 1.0,
        traj_max_len=None,
        graphics: GraphicsConfig = DEFAULT_GRAPHICS,
        **kwargs,
    ):
        super().__init__()
        self.icon = Icon3D(robot_type=robot_type, size=size)
        self.traj = Trajectory(max_len=traj_max_len)

        # A caller-supplied line_width applies to the trajectory (icons are faces).
        traj_lw = kwargs.pop("line_width", graphics.trajectory_size * size)
        self.add("icon", self.icon, **kwargs)
        self.add("trajectory", self.traj, follow_pose=False, line_width=traj_lw, **kwargs)

        if axes:
            self.axes = Axes(size=size, graphics=graphics)
            self.add("axes", self.axes, recolor=False, **kwargs)
        else:
            self.axes = None

    def set_traj_points(self, new_points: np.ndarray) -> None:
        self.traj.set_points(new_points)


class Sphere(SceneObjectGroup):
    """A sphere for visualization: a transparent surface with optional grids.

    Toggle a basic lat/long wireframe (``grid``) and/or bold geodesic meridians
    (``geodesics``). This is the backdrop other canvases use to show the sphere;
    for a functional reference frame (axes + labels) use :class:`SphereGrid`.
    """

    def __init__(
        self,
        radius: float = 1.0,
        color: str = "lightgray",
        opacity: float = 0.05,
        grid: bool = True,
        geodesics: bool = False,
        lw: float = 3.0,
        lw_minor: float = 1.0,
        resolution: int = 30,
        **kwargs,
    ):
        super().__init__()

        from ..meshes import create_geodesic, create_sphere_grid, make_dashed_line

        kw_main = {"line_width": lw, **kwargs}
        kw_minor = {"line_width": lw_minor, **kwargs}

        # Transparent surface
        surface = pv.Sphere(radius=radius, theta_resolution=resolution, phi_resolution=resolution)
        self.add("surface", SceneObject(surface), color=color, opacity=opacity)

        # Bold equator whenever any grid lines are shown
        if grid or geodesics:
            lat_mid = create_sphere_grid(radius=radius, lat_step=90, lon_step=None)
            self.add("lat_mid", SceneObject(lat_mid), color="black", **kw_main)

        # Fine lat/long wireframe
        if grid:
            mesh_fine = create_sphere_grid(radius=radius, lat_step=15, lon_step=15)
            self.add("fine_grid", SceneObject(mesh_fine), color="grey", **kw_minor)

        # Bold meridians: geodesic (solid + dashed) or a plain longitude circle
        if geodesics:
            geo1 = create_geodesic((-89.9, 0), (90, 0), radius=radius, n_points=40)
            geo1_d = make_dashed_line(
                create_geodesic((-90.1, 0), (90, 0), radius=radius, n_points=60), dash_length=3
            )
            geo2 = create_geodesic((-89.9, 90), (90, 90), radius=radius, n_points=40)
            geo2_d = make_dashed_line(
                create_geodesic((-90.1, 90), (90, 90), radius=radius, n_points=60), dash_length=2
            )
            self.add("geo_line1", SceneObject(geo1), color="black", **kw_main)
            self.add("geo_line1_dashed", SceneObject(geo1_d), color="black", **kw_main)
            self.add("geo_line2", SceneObject(geo2), color="black", **kw_main)
            self.add("geo_line2_dashed", SceneObject(geo2_d), color="black", **kw_main)
        elif grid:
            lon_mid = create_sphere_grid(radius=radius, lat_step=None, lon_step=90)
            self.add("lon_mid", SceneObject(lon_mid), color="black", **kw_main)


class SphereGrid(SceneObjectGroup):
    """A functional spherical reference grid.

    A :class:`Sphere` backdrop plus X/Y/Z axis arrows centred at the origin and their
    labels - the spherical analogue of the box ``CanvasGrid`` (e.g. for the 3D attitude
    plotter). Tick labels along the sphere are intentionally omitted for now.
    """

    def __init__(
        self,
        radius: float = 1.0,
        axis_labels=("X", "Y", "Z"),
        axis_colors=("red", "green", "blue"),
        arrow_scale: float = 1.2,
        axis_thickness: float = 0.2,
        label_offset: float = 1.28,
        font_size: int = 18,
        grid: bool = True,
        geodesics: bool = False,
        sphere_color: str = "lightgray",
        sphere_opacity: float = 0.05,
        **kwargs,
    ):
        super().__init__()

        # Sphere backdrop (grid/geodesics forwarded)
        self.sphere = Sphere(
            radius=radius,
            color=sphere_color,
            opacity=sphere_opacity,
            grid=grid,
            geodesics=geodesics,
            **kwargs,
        )
        self.add("sphere", self.sphere, recolor=False)

        # X/Y/Z arrows at the origin + billboard labels at the tips
        tips = []
        for i, (label, color) in enumerate(zip(axis_labels, axis_colors, strict=True)):
            direction = np.eye(3)[i]
            arrow = Vector(
                (0.0, 0.0, 0.0),
                direction,
                scale=radius * arrow_scale,
                thickness=axis_thickness,
                tip_length=axis_thickness * 0.5,
            )
            self.add(f"axis_{label}", arrow, recolor=False, color=color)
            tips.append(direction * radius * label_offset)

        self.add(
            "labels",
            Label(np.asarray(tips), list(axis_labels), font_size=font_size),
            recolor=False,
            follow_pose=False,
        )
