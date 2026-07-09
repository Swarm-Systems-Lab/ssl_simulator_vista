"""Composite scene objects built from primitives (grouped, rigid where relevant)."""

__all__ = ["Axes", "Robot2D", "Robot3D", "SphereGrid"]

import numpy as np
import pyvista as pv

from ..configs import DEFAULT_GRAPHICS, GraphicsConfig
from .base import SceneObject, SceneObjectGroup
from .primitives import Icon2D, Icon3D, StraightLine, Trajectory


class Axes(SceneObjectGroup):
    """The x/y/z attitude axes as a rigid group (posed via ``set_pose``)."""

    def __init__(
        self,
        size: float = 1.0,
        axis_colors=None,
        graphics: GraphicsConfig = DEFAULT_GRAPHICS,
        **kwargs,
    ):
        super().__init__()
        if axis_colors is None:
            axis_colors = {"x": "red", "y": "green", "z": "blue"}

        kwargs.setdefault("line_width", graphics.axes_line_width * size)
        line_length = kwargs.pop("line_length", size)

        origin = np.zeros(3)
        for i, (label, color) in enumerate(axis_colors.items()):
            end = origin + line_length * np.eye(3)[i]
            line = StraightLine(origin, end)
            # recolor=False keeps each axis its own color when a parent recolors.
            self.add(label, line, recolor=False, color=color, **kwargs)


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


class SphereGrid(SceneObjectGroup):
    """The sphere-grid backdrop used by the 3D attitude plotter.

    Fine lat/long wireframe, bold mid axes, solid + dashed geodesics, and a
    transparent sphere.
    """

    def __init__(
        self,
        radius: float = 1.0,
        color: str = "lightgray",
        show_geodesics: bool = True,
        lw: float = 3.0,
        lw_minor: float = 1.0,
        **kwargs,
    ):
        super().__init__()

        from ..meshes import create_geodesic, create_sphere_grid, make_dashed_line

        mesh_fine = create_sphere_grid(radius=radius, lat_step=15, lon_step=15)
        lat_mid = create_sphere_grid(radius=radius, lat_step=90, lon_step=None)

        if show_geodesics:
            geo1 = create_geodesic((-89.9, 0), (90, 0), radius=radius, n_points=40)
            geo1_d = make_dashed_line(
                create_geodesic((-90.1, 0), (90, 0), radius=radius, n_points=60), dash_length=3
            )
            geo2 = create_geodesic((-89.9, 90), (90, 90), radius=radius, n_points=40)
            geo2_d = make_dashed_line(
                create_geodesic((-90.1, 90), (90, 90), radius=radius, n_points=60), dash_length=2
            )
        else:
            lon_mid = create_sphere_grid(radius=radius, lat_step=None, lon_step=90)

        sphere = pv.Sphere(radius=radius, theta_resolution=30, phi_resolution=30)

        kw_main = {"line_width": lw, **kwargs}
        kw_minor = {"line_width": lw_minor, **kwargs}

        self.add("fine_grid", SceneObject(mesh_fine), color="grey", **kw_minor)
        self.add("lat_mid", SceneObject(lat_mid), color="black", **kw_main)
        if show_geodesics:
            self.add("geo_line1", SceneObject(geo1), color="black", **kw_main)
            self.add("geo_line1_dashed", SceneObject(geo1_d), color="black", **kw_main)
            self.add("geo_line2", SceneObject(geo2), color="black", **kw_main)
            self.add("geo_line2_dashed", SceneObject(geo2_d), color="black", **kw_main)
        else:
            self.add("lon_mid", SceneObject(lon_mid), color="black", **kw_main)

        self.add("sphere", SceneObject(sphere), color=color, opacity=0.05)
