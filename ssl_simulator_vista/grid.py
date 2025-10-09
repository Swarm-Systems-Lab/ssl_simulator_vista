import os
import sys
from turtle import position
import numpy as np
import pyvista as pv
from PyQt5.QtWidgets import QGridLayout, QWidget
from PyQt5.QtCore import QTimer

from plotters._base_py_plotter import BaseVisualPlotter
from ssl_simulator.visualization import PlotBase

DEBUG = False

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
                        if DEBUG:
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