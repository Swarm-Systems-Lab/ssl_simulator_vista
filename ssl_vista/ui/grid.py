__all__ = [
    "SimulationGrid",
    "load_grid_from_json"
]

import json
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import QGridLayout, QWidget, QSplitter, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal

from ssl_vista import CONFIG, BasePlotter
from ssl_vista.plotters import *

from ssl_simulator import load_class_from_file

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
    def __init__(self, parent=None, shape=(1,1)):
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

        self._main_splitter = QSplitter(Qt.Orientation.Vertical) # divides rows
        layout.addWidget(self._main_splitter)
        for row in range(shape[0]):
            row_splitter = QSplitter(Qt.Orientation.Horizontal) # divides columns
            self._main_splitter.addWidget(row_splitter)
            self._splitter_rows.append(row_splitter)
        
        # Create an array to store plotter objects
        self._plotter_array = np.full(self._shape, None, dtype=object)

    def add_plotter(self, plotter, position=None):
        if not isinstance(plotter, BasePlotter):
            raise TypeError("Plotter must be an instance of BasePlotter.")

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
            
            widget = plotter.get_widget() if hasattr(plotter, "get_widget") else plotter
            self._splitter_rows[i].addWidget(widget)

        # for i in range(1):
        #     for j in range(3):
        #         label = QLabel(f"Plotter ({i}, {j})")
        #         label.setStyleSheet(f"background-color: hsl({i*80 + j*40}, 70%, 60%);")
        #         label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        #         self._add_plotter(label, (i, j))

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
        """Reset all subplots (optional customization point)."""
        for plotter in self._plotter_array.flatten():
            if plotter is not None:
                plotter.reset_scene(sim_data, sim_settings)

    def update_scenes(self, sim_data, idx):
        """Update each subplot with simulation data at timestep 'idx'."""
        for plotter in self._plotter_array.flatten():
            if plotter is not None:
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

        # Check if this plotter should be loaded dynamically from file
        module_path = plotter_data.get("module_path")
        class_name = plotter_data.get("class_name")

        if plotter_type == "PlotterMpl":
            if module_path and class_name:
                module_path = (file_path.parent / module_path).resolve()
                plotter_cls = load_class_from_file(module_path, class_name)
                plotter = plotter_cls(context = grid.context, **args)
                if CONFIG["DEBUG"]:
                    print(f"[DEBUG] Loaded custom plotter '{class_name}' from '{module_path}'")
            else:
                raise ValueError(str(file_path) + ": 'module_path' and 'class_name' must be specified for custom matplotlib plotters.")
        else:
            # Use built-in factory (dynamically instantiate the plotter based on type)
            plotter = _create_plotter(plotter_type, grid.context, **args)

        # Add to grid
        grid.add_plotter(plotter, position=position)

    if CONFIG["DEBUG"]:
        print(f"[DEBUG] Loaded grid from {file_path} with shape={shape} and {len(plotters)} plotters.")

    return grid

# -------------------------------------------------------------------------
# Helper factory for plotters
# -------------------------------------------------------------------------
def _create_plotter(plotter_type: str, context: dict = None, **kwargs):
    """
    Create a plotter object dynamically from its class name.
    Extend this when adding new plotter types.
    """
    plotter_cls = globals().get(plotter_type)
    if plotter_cls is None:
        raise ValueError(f"Unknown plotter type: {plotter_type}")
    return plotter_cls(context=context, **kwargs)
