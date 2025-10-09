import json
from pathlib import Path

from grid import SimulationGrid
from plotters import *

DEBUG = False

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

    if DEBUG:
        print(f"Loaded grid from {file_path} with shape={shape} and {len(plotters)} plotters.")

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
