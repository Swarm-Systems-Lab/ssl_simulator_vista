"""Public, dependency-light schema and builder for ssl-vista grid layouts.

This module is the **single source of truth** for the on-disk layout format
consumed by :func:`ssl_vista.load_grid_from_json`. It is deliberately free of Qt
and PyVista imports so that *producers* - simulators writing artifacts, tests,
tooling - can construct and validate layouts without a display or the rendering
stack::

    from ssl_vista.layout import LayoutBuilder

    layout = (
        LayoutBuilder(shape=(2, 1))
        .add_canvas_2d((0, 0), robot={"type": "unicycle", "color": "royalblue"})
        .add_mpl((1, 0), module_path="my_plotter.py", class_name="MyPlotter")
        .build()
    )
    layout.write_json("layout.json")

The validated model (:class:`GridLayoutConfig`) is exactly what the viewer parses
at load time, so a layout that builds here is guaranteed schema-valid there -
there is no parallel schema to drift out of sync.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, model_validator

__all__ = [
    "GridLayoutConfig",
    "LayoutBuilder",
    "LayoutSchemaError",
    "PlotterConfig",
    "parse_layout_config",
]

# Plotter type names that render robots and therefore accept a ``robot`` namespace.
_CANVAS_TYPES: dict[str, int] = {"Plotter2DCanvas": 2, "Plotter3DCanvas": 3}


class LayoutSchemaError(ValueError):
    """Raised when a grid layout file fails schema validation."""


class PlotterConfig(BaseModel):
    """Validated configuration for a single plotter entry in a layout file."""

    model_config = ConfigDict(extra="forbid")

    type: str = "Plotter2DCanvas"
    position: tuple[StrictInt, StrictInt] = (0, 0)
    args: dict[str, Any] = Field(default_factory=dict)
    module_path: str | None = None
    class_name: str | None = None

    @model_validator(mode="after")
    def validate_dynamic_fields(self) -> PlotterConfig:
        if (self.module_path is None) ^ (self.class_name is None):
            raise ValueError("'module_path' and 'class_name' must be provided together.")

        if self.type == "BaseMplPlotter" and (self.module_path is None or self.class_name is None):
            raise ValueError(
                "Plotter type 'BaseMplPlotter' requires both 'module_path' and 'class_name'."
            )

        return self


class GridLayoutConfig(BaseModel):
    """Validated root configuration for a simulation grid layout."""

    model_config = ConfigDict(extra="forbid")

    shape: tuple[StrictInt, StrictInt] = (1, 1)
    plotters: list[PlotterConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_shape_and_positions(self) -> GridLayoutConfig:
        rows, cols = self.shape
        if rows < 1 or cols < 1:
            raise ValueError("'shape' values must be positive integers.")

        occupied: set[tuple[int, int]] = set()
        for plotter in self.plotters:
            row, col = plotter.position

            if not (0 <= row < rows and 0 <= col < cols):
                raise ValueError(
                    f"Plotter position {plotter.position} is out of bounds for shape {self.shape}."
                )

            if plotter.position in occupied:
                raise ValueError(f"Duplicate plotter position detected: {plotter.position}.")
            occupied.add(plotter.position)

        return self

    # -- serialization -----------------------------------------------------
    def to_dict(self, *, exclude_none: bool = True) -> dict[str, Any]:
        """Return a JSON-native dict (tuples become lists) ready for ``json.dump``."""
        return self.model_dump(mode="json", exclude_none=exclude_none)

    def to_json(self, *, indent: int = 2, exclude_none: bool = True) -> str:
        """Serialize to a JSON string with a trailing newline."""
        return json.dumps(self.to_dict(exclude_none=exclude_none), indent=indent) + "\n"

    def write_json(self, path: str | Path, *, indent: int = 2, exclude_none: bool = True) -> Path:
        """Write the layout to *path* and return it."""
        path = Path(path)
        path.write_text(self.to_json(indent=indent, exclude_none=exclude_none), encoding="utf-8")
        return path


def parse_layout_config(raw_layout: dict[str, Any], source: Path | None = None) -> GridLayoutConfig:
    """Parse and validate a raw layout dictionary into GridLayoutConfig."""
    try:
        return GridLayoutConfig.model_validate(raw_layout)
    except ValidationError as error:
        source_label = str(source) if source is not None else "layout data"
        raise LayoutSchemaError(f"Invalid layout schema in '{source_label}':\n{error}") from error


class LayoutBuilder:
    """Fluent, validated builder for :class:`GridLayoutConfig`.

    Every ``add_*`` method returns ``self`` for chaining; :meth:`build` runs the
    same pydantic validation the viewer applies at load time (grid bounds, unique
    positions, custom-plotter field pairing).
    """

    def __init__(self, shape: tuple[int, int] = (1, 1)) -> None:
        self._shape = tuple(shape)
        self._plotters: list[PlotterConfig] = []

    def add(
        self,
        plotter_type: str,
        position: tuple[int, int],
        *,
        args: dict[str, Any] | None = None,
        module_path: str | None = None,
        class_name: str | None = None,
    ) -> LayoutBuilder:
        """Add an arbitrary plotter entry. Prefer the ``add_*`` shortcuts below."""
        self._plotters.append(
            PlotterConfig(
                type=plotter_type,
                position=tuple(position),
                args=dict(args or {}),
                module_path=module_path,
                class_name=class_name,
            )
        )
        return self

    def add_canvas_2d(
        self,
        position: tuple[int, int],
        *,
        robot: dict[str, Any] | None = None,
        grid: dict[str, Any] | None = None,
        camera: dict[str, Any] | None = None,
        graphics: dict[str, Any] | None = None,
    ) -> LayoutBuilder:
        """Add a ``Plotter2DCanvas`` with typed config namespaces as ``args``."""
        return self.add(
            "Plotter2DCanvas", position, args=self._canvas_args(robot, grid, camera, graphics)
        )

    def add_canvas_3d(
        self,
        position: tuple[int, int],
        *,
        robot: dict[str, Any] | None = None,
        grid: dict[str, Any] | None = None,
        camera: dict[str, Any] | None = None,
        graphics: dict[str, Any] | None = None,
    ) -> LayoutBuilder:
        """Add a ``Plotter3DCanvas`` with typed config namespaces as ``args``."""
        return self.add(
            "Plotter3DCanvas", position, args=self._canvas_args(robot, grid, camera, graphics)
        )

    def add_mpl(
        self,
        position: tuple[int, int],
        *,
        module_path: str,
        class_name: str,
        args: dict[str, Any] | None = None,
    ) -> LayoutBuilder:
        """Add a file-loaded ``BaseMplPlotter`` (custom Matplotlib plotter plugin)."""
        return self.add(
            "BaseMplPlotter", position, args=args, module_path=module_path, class_name=class_name
        )

    def build(self, *, check_robot_types: bool = False) -> GridLayoutConfig:
        """Return a validated :class:`GridLayoutConfig`.

        With ``check_robot_types=True`` the builder additionally validates each
        canvas plotter's ``robot["type"]`` against
        :meth:`RobotFactory.pose_fields`. This is opt-in because it pulls in the
        PyVista rendering stack; the default keeps layout building dependency-light.
        (Unknown types are rejected by the viewer at load time regardless.)
        """
        config = GridLayoutConfig(shape=self._shape, plotters=list(self._plotters))
        if check_robot_types:
            _validate_canvas_robot_types(config)
        return config

    @staticmethod
    def _canvas_args(
        robot: dict[str, Any] | None,
        grid: dict[str, Any] | None,
        camera: dict[str, Any] | None,
        graphics: dict[str, Any] | None,
    ) -> dict[str, Any]:
        namespaces = {"robot": robot, "grid": grid, "camera": camera, "graphics": graphics}
        return {name: value for name, value in namespaces.items() if value is not None}


def _validate_canvas_robot_types(config: GridLayoutConfig) -> None:
    """Validate canvas robot types via ``RobotFactory`` (imports the PyVista stack)."""
    from ssl_vista.plotters.pv_utils.factories import RobotFactory

    for plotter in config.plotters:
        dimension = _CANVAS_TYPES.get(plotter.type)
        if dimension is None:
            continue
        robot = plotter.args.get("robot")
        if isinstance(robot, dict) and "type" in robot:
            # Raises ValueError (-> propagated) for an unknown robot type.
            RobotFactory.pose_fields(robot["type"], dimension)
