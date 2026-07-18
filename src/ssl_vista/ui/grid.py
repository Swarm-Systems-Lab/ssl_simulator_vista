from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PyQt5.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QSplitter, QVBoxLayout, QWidget

from ssl_vista.plotters import _BasePlotter
from ssl_vista.plotters.registry import create_plotter_instance

from ..layout import parse_layout_config

if TYPE_CHECKING:
    from ssl_vista.types import GridSpec

_logger = logging.getLogger(__name__)


class SimulationGridContext(QObject):
    """
    A context class for SimulationGrid to share variables and signals.
    """

    robot_focus_changed = pyqtSignal(object)  # Signal emitted when robot focus changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._robot_focus = None
        self._prev_robot_focus = None

    @property
    def robot_focus(self):
        return self._robot_focus

    @property
    def prev_robot_focus(self):
        return self._prev_robot_focus

    @robot_focus.setter
    def robot_focus(self, value):
        if self._robot_focus != value:
            self._prev_robot_focus = self._robot_focus
            self._robot_focus = value
            self.robot_focus_changed.emit(value)


class SimulationGrid(QWidget):
    """A customizable grid layout for plotters."""

    def __init__(self, parent=None, shape=(1, 1)):
        super().__init__(parent=parent)
        self.timer = QTimer(self)

        # Grid context
        self.context = SimulationGridContext()

        # Create the grid using splitters
        self._shape = shape
        self._splitter_rows = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._main_splitter = QSplitter(Qt.Orientation.Vertical)  # divides rows
        layout.addWidget(self._main_splitter)
        for _row in range(shape[0]):
            row_splitter = QSplitter(Qt.Orientation.Horizontal)  # divides columns
            self._main_splitter.addWidget(row_splitter)
            self._splitter_rows.append(row_splitter)

        # Create an array to store plotter objects
        self._plotter_array = np.full(self._shape, None, dtype=object)

    def add_plotter(self, plotter, position=None):
        if not isinstance(plotter, _BasePlotter):
            raise TypeError("Plotter must be an instance of _BasePlotter.")

        if position is None:
            # Find the next free position in the grid
            for i in range(self._shape[0]):
                for j in range(self._shape[1]):
                    if self._plotter_array[i, j] is None:
                        self._plotter_array[i, j] = plotter
                        self._splitter_rows[i].addWidget(plotter.get_widget())
                        _logger.debug(f"Added plotter at position ({i}, {j})")
                        return
            raise ValueError("No free position available in the grid.")
        else:
            i, j = position

            if not (0 <= i < self._shape[0] and 0 <= j < self._shape[1]):
                raise ValueError(f"Position {position} is out of bounds.")

            if self._plotter_array[i, j] is not None:
                raise ValueError(f"Position {position} is already occupied.")

            self._plotter_array[i, j] = plotter

            widget = plotter.get_widget() if hasattr(plotter, "get_widget") else plotter
            self._splitter_rows[i].addWidget(widget)

    def save_splitter_state(self):
        """Return byte array for restoring layout later."""
        return self._main_splitter.saveState()

    def restore_splitter_state(self, state):
        """Restore layout from saved splitter state."""
        self._main_splitter.restoreState(state)

    # ---------------------------------------------------------------
    # SCENE MANAGEMENT METHODS
    # ---------------------------------------------------------------

    def setup_scenes(self):
        """Initialize scenes for all subplots."""
        for plotter in self._plotter_array.flatten():
            if plotter is not None:
                plotter.setup_scene()

    def reset_scenes(self, sim_data, sim_settings):
        """Reset all subplots and emit a single structured log record."""
        for plotter in self._plotter_array.flatten():
            if plotter is not None:
                plotter.reset_scene(sim_data, sim_settings)

        if _logger.isEnabledFor(logging.DEBUG):
            snapshots = {}
            rows, cols = self._plotter_array.shape
            for r in range(rows):
                for c in range(cols):
                    plotter = self._plotter_array[r, c]
                    if plotter is None:
                        continue
                    snapshots[f"({r},{c})"] = plotter.collect_scene_objects()

            _logger.debug(
                "grid scenes reset",
                extra={"grid_shape": [rows, cols], "plotters": snapshots},
            )

    def update_scenes(self, sim_data, idx):
        """Update each subplot with simulation data at timestep 'idx'."""
        for plotter in self._plotter_array.flatten():
            if plotter is not None:
                plotter.update_all_scene_objects(sim_data, idx)

    def reset_views(self):
        """Restore the initial camera/view state for all subplots."""
        for plotter in self._plotter_array.flatten():
            if plotter is not None:
                plotter.reset_view()

    # ---------------------------------------------------------------
    # TIMER METHODS
    # ---------------------------------------------------------------

    def timer_set(self, callback, step=50):
        """Set the timer callback and interval."""
        self.timer.timeout.connect(callback)
        self.timer.setInterval(step)

    def timer_start(self):
        """Start the simulation update timer."""
        self.timer.start()

    def timer_stop(self):
        """Stop the simulation update timer."""
        self.timer.stop()


######################################################################################
# GRID LOADER FUNCTIONS


def load_grid_from_json(file_path: str | Path, parent=None) -> SimulationGrid:
    """
    Load and configure a SimulationGrid instance from a JSON layout file.

    Parameters
    ----------
    file_path : str | Path
        Path to the JSON configuration file.
    parent : QWidget, optional
        Parent widget for the grid.

    Returns
    -------
    SimulationGrid
        A fully configured SimulationGrid instance.
    """

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Grid layout file not found: {file_path}")

    with open(file_path) as f:
        layout_data = json.load(f)

    layout_config = parse_layout_config(layout_data, source=file_path)

    # Read grid shape
    shape = layout_config.shape
    grid = SimulationGrid(parent=parent, shape=shape)

    # Load plotters info
    for plotter_data in layout_config.plotters:
        plotter = create_plotter_instance(
            plotter_data.type,
            context=grid.context,
            module_path=plotter_data.module_path,
            class_name=plotter_data.class_name,
            base_dir=file_path.parent,
            **plotter_data.args,
        )

        # Add to grid
        grid.add_plotter(plotter, position=plotter_data.position)

    _logger.debug(
        f"Loaded grid layout from {file_path} with shape {shape} and {len(layout_config.plotters)} plotters."
    )

    return grid


def load_grid_from_spec(spec: GridSpec, parent: object = None) -> SimulationGrid:
    """Build a :class:`SimulationGrid` from a programmatic :class:`~ssl_vista.types.GridSpec`.

    This is the programmatic counterpart to :func:`load_grid_from_json` - it
    accepts a :class:`~ssl_vista.types.GridSpec` Python object rather than a
    JSON file path, so no filesystem access is required.

    Parameters
    ----------
    spec:
        A :class:`~ssl_vista.types.GridSpec` describing the grid shape and each
        plotter cell (by class object or registry name).
    parent:
        Optional parent widget.

    Returns
    -------
    SimulationGrid
        A fully configured :class:`SimulationGrid` instance ready to be used
        as a central widget.
    """
    grid = SimulationGrid(parent=parent, shape=spec.shape)

    for plotter_spec in spec.plotters:
        if plotter_spec.plotter_cls is not None:
            plotter = create_plotter_instance(
                plotter_spec.plotter_cls,
                context=grid.context,
                **plotter_spec.kwargs,
            )
        else:
            # plotter_type is guaranteed non-None by PlotterSpec.__post_init__
            assert plotter_spec.plotter_type is not None  # noqa: S101
            plotter = create_plotter_instance(
                plotter_spec.plotter_type,
                context=grid.context,
                **plotter_spec.kwargs,
            )

        grid.add_plotter(plotter, position=plotter_spec.position)

    _logger.debug(
        f"Loaded grid from spec with shape {spec.shape} and {len(spec.plotters)} plotters."
    )

    return grid
