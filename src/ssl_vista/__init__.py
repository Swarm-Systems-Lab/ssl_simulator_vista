"""
SSL Simulator Vista - A PyVista/Matplotlib-based Visualization Tool for the SSL Simulator
"""

# Only expose CONFIG at the top level to avoid circular imports
from .config import CONFIG

# Programmatic API types (no Qt / heavy-dependency imports at this level)
from .types import GridSpec, PlotterSpec, SimData, SimSettings

__all__ = [
    "CONFIG",
    "BaseCanvasPlotter",
    "BaseMplPlotter",
    "GridSpec",
    "PlotterSpec",
    "SimData",
    "SimSettings",
    "load_grid_from_json",
    "load_grid_from_spec",
    "run_app",
]


def __getattr__(name: str):
    """Lazily resolve Qt-dependent names to avoid circular imports at package load time."""
    if name == "run_app":
        from .app import run_app
        return run_app
    
    if name in ("load_grid_from_json", "load_grid_from_spec"):
        from .ui.grid import load_grid_from_json, load_grid_from_spec
        return load_grid_from_json if name == "load_grid_from_json" else load_grid_from_spec
    
    if name == "BaseMplPlotter":
        from .plotters.base_mpl import BaseMplPlotter
        return BaseMplPlotter
    
    if name == "BaseCanvasPlotter":
        from .plotters.base_canvas import BaseCanvasPlotter
        return BaseCanvasPlotter
    
    raise AttributeError(f"module 'ssl_vista' has no attribute {name!r}")
