from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, model_validator


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


def parse_layout_config(raw_layout: dict[str, Any], source: Path | None = None) -> GridLayoutConfig:
    """Parse and validate a raw layout dictionary into GridLayoutConfig."""
    try:
        return GridLayoutConfig.model_validate(raw_layout)
    except ValidationError as error:
        source_label = str(source) if source is not None else "layout data"
        raise LayoutSchemaError(f"Invalid layout schema in '{source_label}':\n{error}") from error
