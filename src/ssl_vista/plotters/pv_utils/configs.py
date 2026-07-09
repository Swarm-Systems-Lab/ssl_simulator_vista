"""Typed configuration models for canvas plotters and their sub-components.

Each canvas element (grid, camera/scene, graphics defaults, robots) owns a pydantic
model here. A plotter accepts a model (or a plain dict, e.g. from a layout file's
``args``) and forwards it *whole* to the sub-component, so sub-component options never
need to be re-declared on every parent class. ``extra="forbid"`` turns a typo in a
config namespace into a loud validation error instead of a silently ignored kwarg.
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_GRAPHICS",
    "CameraConfig",
    "GraphicsConfig",
    "GridConfig",
    "RobotConfig",
]

from typing import Union

from pydantic import BaseModel, ConfigDict


class _BaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def build(cls, value: _BaseConfig | dict | None, **defaults):
        """Coerce ``None`` / dict / instance into an instance.

        ``defaults`` provide lower-priority values (e.g. per-plotter defaults) that a
        dict ``value`` overrides key-by-key. An instance ``value`` is returned as-is.
        """
        if isinstance(value, cls):
            return value
        data = dict(defaults)
        if value is not None:
            data.update(value)
        return cls.model_validate(data)


class GridConfig(_BaseConfig):
    """Configuration for :class:`~ssl_vista.plotters.pv_utils.canvas_grid.CanvasGrid`."""

    range: float | list[float] | None = None
    ticks: int | list[int] | None = None
    font_size: int = 15
    xtitle: str = "X"
    ytitle: str = "Y"
    ztitle: str = "Z"
    bold: bool = False
    color: str = "black"
    grid: bool = True
    minor_ticks: bool = True
    use_3d_text: bool = False

    def show_bounds_style(self) -> dict:
        """The subset of fields forwarded to PyVista ``show_bounds``."""
        return {
            "font_size": self.font_size,
            "xtitle": self.xtitle,
            "ytitle": self.ytitle,
            "ztitle": self.ztitle,
            "bold": self.bold,
            "color": self.color,
            "grid": self.grid,
            "minor_ticks": self.minor_ticks,
            "use_3d_text": self.use_3d_text
        }


class CameraConfig(_BaseConfig):
    """Camera / background / lighting for a canvas scene.

    ``None`` fields resolve to per-dimension defaults (2D: parallel top-down; 3D:
    perspective iso), so a caller only overrides what they care about.
    """

    background: str = "white"
    position: str | None = None
    parallel: bool | None = None
    lights: str | None = None  # "three" | "2d" | "none"
    azimuth: float | None = None

    def resolved(self, dimension: int) -> dict:
        is_2d = dimension == 2
        return {
            "background": self.background,
            "position": self.position or ("xy" if is_2d else "iso"),
            "parallel": self.parallel if self.parallel is not None else is_2d,
            "lights": self.lights or ("2d" if is_2d else "three"),
            "azimuth": self.azimuth,
        }


class GraphicsConfig(_BaseConfig):
    """Default line sizes for scene objects (replaces the old global ``GCONF``)."""

    axes_line_width: float = 4.0
    axes_line_length: float = 0.3
    trajectory_size: float = 4.0
    trajectory_opacity: float = 0.5
    grid_line_width: float = 0.8


class RobotConfig(_BaseConfig):
    """Per-robot style used by the concrete canvas plotters."""

    type: str = "unicycle"
    color: str = "blue"
    size: float = 0.25
    tail: int | None = 500
    axes: bool = True

    @classmethod
    def resolve(cls, namespace=None, defaults=None, **flat):
        """Build from a ``robot`` namespace plus deprecated flat aliases.

        Priority: namespace/flat values > ``defaults``. Flat aliases equal to ``None``
        are ignored (the "unset" sentinel for the deprecated ``robot_*`` kwargs). An
        instance ``namespace`` is returned unchanged.
        """
        if isinstance(namespace, cls):
            return namespace
        over = dict(namespace or {})
        for key, value in flat.items():
            if value is not None:
                over.setdefault(key, value)
        return cls.build(over, **(defaults or {}))


#: Fallback graphics defaults used when a scene object is built without an explicit one.
DEFAULT_GRAPHICS = GraphicsConfig()
