__all__ = ["Plotter2DCanvas"]

from .base_canvas import BaseCanvasPlotter
from .pv_utils.configs import RobotConfig

_ROBOT_DEFAULTS = {"type": "unicycle", "color": "blue", "size": 0.25, "tail": 500}


class Plotter2DCanvas(BaseCanvasPlotter):
    """
    2D PyVista canvas for visualizing robots, trajectories, and vectors.

    Directional types (``unicycle``, ``car``, ``fixed_wing``) are oriented by a planar
    heading read from ``label_heading`` with shape ``(T, N)``; symmetric types
    (``single_integrator``) are drawn from position alone. The shared lifecycle and the
    "which fields are required" policy live in :class:`BaseCanvasPlotter`.
    """

    def __init__(
        self,
        *,
        robot=None,
        grid=None,
        camera=None,
        graphics=None,
        label_pos="p",
        label_heading="theta",
        parent=None,
        context=None,
    ):
        robot_cfg = RobotConfig.resolve(robot, defaults=_ROBOT_DEFAULTS)
        super().__init__(
            dimension=2,
            parent=parent,
            context=context,
            grid=grid,
            camera=camera,
            graphics=graphics,
            robot=robot_cfg,
            label_pos=label_pos,
            label_orientation=label_heading,
        )

    # ---------------------------------------------------------------
    # DIMENSION-SPECIFIC HOOKS
    # ---------------------------------------------------------------
    def _pose_kwargs(self, orientation_value) -> dict:
        return {"heading": orientation_value}

    def _check_orientation_shape(self, arr, n_robots) -> None:
        if arr.ndim != 2 or arr.shape[1] != n_robots:
            raise ValueError(f"Heading array must be shape (T,N={n_robots}), got {arr.shape}")
