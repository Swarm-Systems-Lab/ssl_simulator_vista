"""
Programmatic API types for ssl_vista.

These types allow consumers to configure and launch the simulation viewer entirely
from Python objects, without touching the filesystem.

Example
-------
>>> from ssl_vista import GridSpec, PlotterSpec, run_app
>>> from ssl_simulator.utils.processing import load_sim
>>> from ssl_vista.plotters import Plotter3DCanvas
>>>
>>> sim_data, sim_settings = load_sim("run.csv")
>>> spec = GridSpec(
...     shape=(1, 2),
...     plotters=[
...         PlotterSpec(position=(0, 0), plotter_cls=Plotter3DCanvas, kwargs={"robot_type": "unicycle"}),
...         PlotterSpec(position=(0, 1), plotter_type="Plotter3DAttitude"),
...     ],
... )
>>> run_app(grid_spec=spec, sim_data=sim_data, sim_settings=sim_settings, auto_play=True)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Simulation-data type aliases
# These mirror the structures returned by ssl_simulator's load_sim utility.
# ---------------------------------------------------------------------------

#: A mapping of array/scalar simulation variables keyed by field name.
#: ``sim_data["time"]`` must be a sequence of monotonically increasing timestamps.
SimData = dict[str, Any]

#: Scalar simulation parameters (e.g. ``dt``, ``n_robots``) produced by load_sim.
SimSettings = dict[str, Any]


# ---------------------------------------------------------------------------
# Grid / plotter spec dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PlotterSpec:
    """Specification for a single plotter within a :class:`GridSpec`.

    Exactly one of *plotter_cls* or *plotter_type* must be supplied.

    Parameters
    ----------
    position:
        ``(row, col)`` cell in the simulation grid.
    plotter_cls:
        A concrete plotter *class* (must be a subclass of ``_BasePlotter``).
        Use this to pass a class object directly without going through the
        string registry.
    plotter_type:
        Name of a plotter registered in the global registry
        (e.g. ``"Plotter3DCanvas"``).
    kwargs:
        Extra keyword arguments forwarded to the plotter constructor.
    """

    position: tuple[int, int]
    plotter_cls: type[Any] | None = None
    plotter_type: str | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.plotter_cls is None and self.plotter_type is None:
            raise ValueError("PlotterSpec requires exactly one of 'plotter_cls' or 'plotter_type'.")
        if self.plotter_cls is not None and self.plotter_type is not None:
            raise ValueError(
                "PlotterSpec accepts only one of 'plotter_cls' or 'plotter_type', not both."
            )


@dataclass
class GridSpec:
    """Specification for a full simulation grid layout.

    Parameters
    ----------
    shape:
        ``(rows, cols)`` dimensions of the plotter grid.
    plotters:
        Ordered list of :class:`PlotterSpec` entries describing each cell.
    """

    shape: tuple[int, int]
    plotters: list[PlotterSpec] = field(default_factory=list)
