__all__ = ["BaseCanvasPlotter"]

from typing import ClassVar

import numpy as np
import pyvista as pv

from ._base_plotters import _BaseVisualPlotter
from .pv_utils.canvas_grid import CanvasGrid
from .pv_utils.configs import CameraConfig, GraphicsConfig, GridConfig, RobotConfig
from .pv_utils.factories import RobotFactory
from .pv_utils.scene import Robot2D, Robot3D


def apply_camera(pvqt, cam: dict) -> None:
    """Apply a resolved :class:`CameraConfig` (see ``CameraConfig.resolved``) to a plotter."""
    pvqt.set_background(cam["background"])
    pvqt.camera_position = cam["position"]
    pvqt.camera.SetParallelProjection(cam["parallel"])
    if cam["lights"] == "2d":
        pvqt.enable_2d_style()
    elif cam["lights"] == "three":
        pvqt.enable_3_lights()
    if cam["azimuth"] is not None:
        pvqt.camera.Azimuth(cam["azimuth"])


class BaseCanvasPlotter(_BaseVisualPlotter):
    """
    Generalized PyVista canvas for spatial visualization.

    Configuration is grouped into namespaces - ``grid`` (:class:`GridConfig`),
    ``camera`` (:class:`CameraConfig`), ``robot`` (:class:`RobotConfig`) and
    ``graphics`` (:class:`GraphicsConfig`) - each accepting a model or a plain dict
    (e.g. from a layout file's ``args``). Each namespace is forwarded whole to its
    sub-component, so options never need re-declaring on this class.

    The robot *type* dictates which simulation fields are required (see
    :meth:`RobotFactory.pose_fields`): every type needs positions, and directional
    types additionally need an orientation - a planar ``heading`` in 2D or a rotation
    matrix (``rotation``) in 3D. Symmetric types (e.g. ``single_integrator``) are drawn
    from position alone. This policy and the shared ``init_artists`` / ``update_artists``
    lifecycle live here; concrete subclasses only supply the small dimension-specific
    hooks below (``_pose_kwargs``, ``_check_orientation_shape``, ``_robot_build_kwargs``).
    """

    #: Name of the orientation field per dimension, as used by ``RobotFactory.pose_fields``.
    _ORIENTATION_FIELD: ClassVar[dict[int, str]] = {2: "heading", 3: "rotation"}

    def __init__(
        self,
        dimension,  # 2 or 3
        *,
        parent=None,
        context=None,
        grid=None,
        camera=None,
        robot=None,
        graphics=None,
        label_pos="p",
        label_orientation=None,
    ):
        super().__init__(parent=parent, context=context)

        self.dimension = dimension
        self._robot_objs = []

        # - Config namespaces (each accepts a model, a dict, or None)
        self.grid_config = GridConfig.build(grid)
        self.camera_config = CameraConfig.build(camera)
        self.graphics = GraphicsConfig.build(graphics)
        self.robot_config = RobotConfig.build(robot)

        # - Type-driven data contract: what fields this platform consumes.
        self.robot_type = self.robot_config.type
        self.required_fields = RobotFactory.pose_fields(self.robot_type, dimension)
        self.orientation_field = self._ORIENTATION_FIELD[dimension]
        self.needs_orientation = self.orientation_field in self.required_fields

        # - Simulation data labels. A symmetric icon ignores orientation, so drop its
        #   label entirely - a single-integrator run isn't forced to provide it.
        self.label_pos = label_pos
        self.label_orientation = label_orientation if self.needs_orientation else None

        # - Canvas grid (whole grid namespace forwarded)
        self.canvas_grid = CanvasGrid(self.pvqt, dimension=dimension, config=self.grid_config)

    # ---------------------------------------------------------------
    # SUBCLASS HOOKS (dimension-specific bits)
    # ---------------------------------------------------------------
    def _pose_kwargs(self, orientation_value) -> dict:
        """Map an orientation sample to the ``set_pose`` kwargs for this dimension
        (2D: ``{"heading": ...}``, 3D: ``{"R": ...}``)."""
        raise NotImplementedError

    def _check_orientation_shape(self, arr, n_robots) -> None:
        """Validate the orientation array's shape; raise ``ValueError`` if wrong."""
        raise NotImplementedError

    def _robot_build_kwargs(self) -> dict:
        """Extra per-robot kwargs for :meth:`add_robot` (e.g. 3D ``axes``)."""
        return {}

    # ---------------------------------------------------------------
    # ARTISTS (shared lifecycle, driven by the hooks above)
    # ---------------------------------------------------------------
    def init_artists(self, sim_data, sim_settings):
        """Build robot icons + trajectory placeholders and pose them at frame 0."""
        self._check_labels(sim_data)
        self._check_data_shapes(sim_data)

        data_pos = sim_data.get(self.label_pos)
        data_orient = self._get_orientation(sim_data)
        n_robots = data_pos.shape[1]

        for i in range(n_robots):
            obj_robot = self.add_robot(
                robot_name=f"robot_{i}",
                icon_type=self.robot_type,
                color=self.robot_config.color,
                size=self.robot_config.size,
                traj_max_len=self.robot_config.tail,
                **self._robot_build_kwargs(),
            )
            pose_kw = self._pose_kwargs(data_orient[0, i]) if data_orient is not None else {}
            obj_robot.set_pose(position=data_pos[0, i], **pose_kw)

    def update_artists(self, sim_data, idx):
        """Update robot poses and trajectory tails for frame ``idx``."""
        data_pos = sim_data.get(self.label_pos)
        data_orient = self._get_orientation(sim_data)

        for i, robot_obj in enumerate(self._robot_objs):
            pose_kw = self._pose_kwargs(data_orient[idx, i]) if data_orient is not None else {}
            robot_obj.set_pose(position=data_pos[idx, i], **pose_kw)

            # Full history; the trajectory trims itself to traj_max_len.
            robot_obj.set_traj_points(data_pos[0:idx, i, :])
            robot_obj.set_visibility(True)

        # - Update the canvas grid center
        new_center = np.array([data_pos[idx, ...].mean(axis=0).tolist()])
        self.set_grid_centroid(new_center)

    # ---------------------------------------------------------------
    # DATA ACCESS / SANITY CHECKS (shared)
    # ---------------------------------------------------------------
    def _get_orientation(self, sim_data):
        """Return the orientation array, or ``None`` when this platform doesn't use one."""
        if not self.needs_orientation:
            return None
        return sim_data.get(self.label_orientation)

    def _check_labels(self, sim_data):
        """Ensure the labels this robot type requires are present in sim_data."""
        if self.label_pos not in sim_data:
            raise ValueError(f"sim_data must contain positions at '{self.label_pos}'")

        if self.needs_orientation:
            if self.label_orientation is None:
                raise ValueError(
                    f"Robot type '{self.robot_type}' is directional and requires a "
                    f"{self.orientation_field}, but its label was set to None."
                )
            if self.label_orientation not in sim_data:
                raise ValueError(
                    f"Robot type '{self.robot_type}' requires a {self.orientation_field} at "
                    f"'{self.label_orientation}', which is missing from sim_data."
                )

    def _check_data_shapes(self, sim_data):
        """Ensure required data arrays have the expected shapes."""
        data_pos = sim_data.get(self.label_pos)
        if data_pos.ndim != 3 or data_pos.shape[2] != self.dimension:
            raise ValueError(
                f"Positions array must be shape (T,N,{self.dimension}), got {data_pos.shape}"
            )

        if self.needs_orientation:
            self._check_orientation_shape(sim_data.get(self.label_orientation), data_pos.shape[1])

    # ---------------------------------------------------------------
    # ARTISTS MANAGEMENT
    # ---------------------------------------------------------------

    def _clear_artists(self):
        """Remove all artists from the scene."""
        self.clear_scene_objects()
        self._robot_objs.clear()

    # ---------------------------------------------------------------
    # CANVAS HELPER METHODS
    # ---------------------------------------------------------------
    def add_robot(self, robot_name, icon_type, visible=True, traj_max_len=None, **kwargs):
        # - Create the robot bundle (trajectory tail self-trims to traj_max_len)
        robot_cls = Robot2D if self.dimension == 2 else Robot3D
        obj_robot = robot_cls(
            icon_type,
            visible=visible,
            traj_max_len=traj_max_len,
            graphics=self.graphics,
            **kwargs,
        )

        self.add_scene_object(robot_name, obj_robot)
        self._robot_objs.append(obj_robot)
        return obj_robot

    def set_grid_centroid(self, centroid):
        """Set the canvas grid centroid."""
        self.canvas_grid.update_center(centroid)

    # ---------------------------------------------------------------
    # SETUP/RESET/UPDATE SCENE
    # ---------------------------------------------------------------
    def setup_scene(self, sim_data=None, sim_settings=None):
        """Set up the scene by initializing the grid and artists."""
        apply_camera(self.pvqt, self.camera_config.resolved(self.dimension))

        # Add a reference grid
        self.canvas_grid.setup_grid()

        # Reset camera
        self.pvqt.reset_camera()

    def reset_scene(self, sim_data=None, sim_settings=None):
        """Reset the scene by clearing and reinitializing artists."""
        self._clear_artists()
        self.init_artists(sim_data, sim_settings)
        self.pvqt.reset_camera()

    def reset_view(self) -> None:
        """Restore initial camera orientation, grid position, and fit the scene."""
        self.canvas_grid.reset()
        cam = self.camera_config.resolved(self.dimension)
        self.pvqt.camera_position = cam["position"]
        self.pvqt.camera.SetParallelProjection(cam["parallel"])
        self.pvqt.reset_camera()

    # ---------------------------------------------------------------
    # SCENE OBJECTS MANAGEMENT
    # ---------------------------------------------------------------
    def get_scene_object(self, obj_name):
        """Retrieve a scene object by name."""
        return self.scene_objects.get(obj_name, None)

    def in_scene(self, names):
        """Check if one or more scene objects exist."""
        if not isinstance(names, (str, tuple)):
            raise TypeError("names must be a string or a tuple of strings")
        if isinstance(names, tuple):
            return all(name in self.scene_objects for name in names)
        return names in self.scene_objects

    # ---------------------------------------------------------------
    # CONTEXT SIGNALS CALLBACKS
    # ---------------------------------------------------------------
    # To be modified by subclasses if needed
    def when_change_robot_focus(self, idx_new_focus, idx_prv_focus):
        """Handle changes in robot focus from the context."""
        if idx_new_focus is not None and len(self._robot_objs) > idx_new_focus:
            if idx_prv_focus is not None and len(self._robot_objs) > idx_prv_focus:
                self._robot_objs[idx_prv_focus].set_focus(False)
            self._robot_objs[idx_new_focus].set_focus(True)
