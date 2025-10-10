__all__ = [
    "SimulationGrid",
    "load_grid_from_json"
]

import json
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import QGridLayout, QWidget
from PyQt5.QtCore import QTimer

from ssl_vista import BaseVisualPlotter
from ssl_vista.plotters import *
from ssl_simulator.visualization import PlotBase

from ssl_vista import CONFIG

class SimulationGrid(QWidget):
    """A customizable grid layout for plotters."""
    def __init__(self, parent=None, shape=(1,1)):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.setLayout(self.layout)
        self.timer = QTimer(self)

        # Create an array to store plotter objects
        self._shape = shape
        self._plotter_array = np.full(self._shape, None, dtype=object)

    def add_plotter(self, plotter: BaseVisualPlotter, position=None):
        if not isinstance(plotter, (BaseVisualPlotter, PlotBase)):
            raise TypeError("Plotter must be an instance of BaseVisualPlotter or PlotBase.")

        if position is None:
            # Find the next free position in the grid
            for i in range(self._shape[0]):
                for j in range(self._shape[1]):
                    if self._plotter_array[i, j] is None:
                        self._plotter_array[i, j] = plotter
                        self.layout.addWidget(plotter.get_widget(), i, j)
                        if CONFIG["DEBUG"]:
                            print(f"[DEBUG] Added plotter at position ({i}, {j})")
                        return
            raise ValueError("No free position available in the grid.")
        else:
            i, j = position
            if not (0 <= i < self._shape[0] and 0 <= j < self._shape[1]):
                raise ValueError(f"Position {position} is out of bounds.")
            if self._plotter_array[i, j] is not None:
                raise ValueError(f"Position {position} is already occupied.")
            self._plotter_array[i, j] = plotter
            self.layout.addWidget(plotter.get_widget(), i, j)

    # ---------------------------------------------------------------
    # SCENE MANAGEMENT METHODS
    # ---------------------------------------------------------------

    def setup_scenes(self):
        """Initialize scenes for all subplots."""
        for plotter in self._plotter_array.flatten():
            plotter.setup_scene()

    def reset_scenes(self, sim_data, sim_settings):
        """Reset all subplots (optional customization point)."""
        for plotter in self._plotter_array.flatten():
            plotter.reset_scene(sim_data, sim_settings)

    def update_scenes(self, sim_data, idx):
        """Update each subplot with simulation data at timestep 'idx'."""
        for plotter in self._plotter_array.flatten():
            plotter.update_all_scene_objects(sim_data, idx)

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

def load_grid_from_json(file_path: str, parent=None) -> SimulationGrid:
    """
    Load and configure a SimulationGrid instance from a JSON layout file.

    Parameters
    ----------
    file_path : str
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

    with open(file_path, "r") as f:
        layout_data = json.load(f)

    # Read grid shape (default = (1, 1))
    shape = tuple(layout_data.get("shape", [1, 1]))
    grid = SimulationGrid(parent=parent, shape=shape)

    # Load plotters info
    plotters = layout_data.get("plotters", [])
    for plotter_data in plotters:
        plotter_type = plotter_data.get("type", "Plotter2DCanvas")
        position = tuple(plotter_data.get("position", (0, 0)))
        args = plotter_data.get("args", {})

        # Dynamically instantiate the plotter based on type
        plotter = _create_plotter(plotter_type, **args)

        # Add to grid
        grid.add_plotter(plotter, position=position)

    if CONFIG["DEBUG"]:
        print(f"[DEBUG] Loaded grid from {file_path} with shape={shape} and {len(plotters)} plotters.")

    return grid


# -------------------------------------------------------------------------
# Helper factory for plotters
# -------------------------------------------------------------------------
def _create_plotter(plotter_type: str, **kwargs):
    """
    Create a plotter object dynamically from its class name.
    Extend this when adding new plotter types.
    """
    plotter_cls = globals().get(plotter_type)
    if plotter_cls is None:
        raise ValueError(f"Unknown plotter type: {plotter_type}")
    return plotter_cls(**kwargs)
