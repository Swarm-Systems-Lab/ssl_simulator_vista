__all__ = ["Plotter3DCanvas"]

from .base_canvas import BaseCanvasPlotter
from .pv_utils.configs import RobotConfig

_ROBOT_DEFAULTS = {"type": "unicycle", "color": "darkgrey", "size": 0.5, "tail": 500, "axes": True}


class Plotter3DCanvas(BaseCanvasPlotter):
    """
    3D PyVista canvas for visualizing robots, trajectories, and vectors.

    Directional types (``unicycle``, ``car``, ``quadrotor``, ``miniplank``) are oriented
    by a rotation matrix read from ``label_rot`` with shape ``(T, N, 3, 3)``; symmetric
    types (``single_integrator``) are drawn from position alone. The shared lifecycle and
    the "which fields are required" policy live in :class:`BaseCanvasPlotter`.
    """

    def __init__(
        self,
        *,
        robot=None,
        grid=None,
        camera=None,
        graphics=None,
        label_pos="robot.p",
        label_rot="robot.R",
        parent=None,
        context=None,
    ):
        robot_cfg = RobotConfig.resolve(robot, defaults=_ROBOT_DEFAULTS)
        super().__init__(
            dimension=3,
            parent=parent,
            context=context,
            grid=grid,
            camera=camera,
            graphics=graphics,
            robot=robot_cfg,
            label_pos=label_pos,
            label_orientation=label_rot,
        )

    # ---------------------------------------------------------------
    # DIMENSION-SPECIFIC HOOKS
    # ---------------------------------------------------------------
    def _robot_build_kwargs(self) -> dict:
        # 3D robots carry an attitude triad; toggle via the robot config.
        return {"axes": self.robot_config.axes}

    def _pose_kwargs(self, orientation_value) -> dict:
        return {"R": orientation_value}

    def _check_orientation_shape(self, arr, n_robots) -> None:
        if arr.ndim != 4 or arr.shape[1] != n_robots or arr.shape[2:] != (3, 3):
            raise ValueError(f"Rotations array must be shape (T,N={n_robots},3,3), got {arr.shape}")
