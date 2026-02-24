from __future__ import annotations

import signal
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, overload

from PyQt5.QtWidgets import QApplication

from ssl_vista.ui import MainWindow

if TYPE_CHECKING:
    from ssl_vista.types import GridSpec, SimData, SimSettings
    from ssl_vista.ui.grid import SimulationGrid


# ---------------------------------------------------------------------------
# Overload signatures  (for static type-checkers / mypy --strict)
# ---------------------------------------------------------------------------


@overload
def run_app(
    *,
    layout: str | Path,
    data_path: str | Path,
    auto_play: bool = ...,
) -> None: ...


@overload
def run_app(
    *,
    grid_spec: GridSpec,
    sim_data: SimData,
    sim_settings: SimSettings,
    auto_play: bool = ...,
) -> None: ...


@overload
def run_app(
    *,
    grid: SimulationGrid,
    sim_data: SimData,
    sim_settings: SimSettings,
    auto_play: bool = ...,
) -> None: ...


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------


def _build_main_window(auto_play: bool, **kwargs: Any) -> MainWindow:
    """Construct and return the appropriate :class:`MainWindow` for the given kwargs.

    Responsible solely for routing between the three call paths and building
    the window object.  Qt application setup and event-loop management are
    handled by the caller (:func:`run_app`).
    """
    # GridSpec path: convert the spec to a grid, then fall through to the
    # pre-built-grid path — avoids duplicating the sim_data/sim_settings pops.
    if "grid_spec" in kwargs:
        from ssl_vista.ui.grid import load_grid_from_spec  # local import to avoid cycles

        kwargs["grid"] = load_grid_from_spec(kwargs.pop("grid_spec"))

    if "grid" in kwargs:
        return MainWindow(
            grid=kwargs.pop("grid"),
            sim_data=kwargs.pop("sim_data"),
            sim_settings=kwargs.pop("sim_settings"),
            auto_play=auto_play,
        )

    # File-based path (original behaviour).
    return MainWindow(
        layout=str(kwargs.pop("layout")),
        data_path=str(kwargs.pop("data_path")),
        auto_play=auto_play,
    )


def run_app(**kwargs: Any) -> None:  # type: ignore[misc]
    """Launch the ssl_vista simulation viewer.

    This function supports three mutually exclusive call signatures:

    **File-based path** (original behaviour — fully preserved)::

        run_app(layout="path/to/layout.json", data_path="path/to/run.csv")

    **GridSpec programmatic path** (build the grid from a spec object)::

        run_app(grid_spec=my_spec, sim_data=sim_data, sim_settings=sim_settings)

    **Pre-built grid programmatic path** (pass an already-constructed grid)::

        run_app(grid=my_grid, sim_data=sim_data, sim_settings=sim_settings)

    Parameters
    ----------
    layout:
        (*File path*) Path to the JSON grid layout file.
    data_path:
        (*File path*) Path to the simulation CSV file.
    grid_spec:
        (*GridSpec path*) A :class:`~ssl_vista.types.GridSpec` describing the
        grid to build programmatically.
    grid:
        (*Pre-built path*) An already-constructed
        :class:`~ssl_vista.ui.grid.SimulationGrid` instance.
    sim_data:
        (*Programmatic paths*) Pre-parsed simulation data dict (same structure as
        returned by ``load_sim``).
    sim_settings:
        (*Programmatic paths*) Scalar simulation parameters dict.
    auto_play:
        Whether to start playback automatically once the window opens.
    """
    auto_play: bool = kwargs.pop("auto_play", False)

    app = QApplication(sys.argv)
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Restore default Ctrl+C handler

    window = _build_main_window(auto_play, **kwargs)
    window.show()
    sys.exit(app.exec())
