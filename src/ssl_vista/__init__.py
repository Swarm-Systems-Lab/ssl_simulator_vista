"""
SSL Simulator Vista - A PyVista/Matplotlib-based Visualization Tool for the SSL Simulator
"""

__version__ = "0.0.2"


import inspect

from . import plotters

# Configuration
from .config import CONFIG

# Data
from .data import *
from .plotters.pv_utils import scene_objects

# Plotters
from .plotters.pv_utils.scene_objects import *

public_classes = []
for name, _obj in inspect.getmembers(plotters, inspect.isclass):
    if name.startswith("Base") or name.startswith("Plotter"):
        public_classes.append(name)


# Collect all __all__ from scene_objects.py
public_classes.extend(scene_objects.__all__)

# Define the public API
__all__ = ["CONFIG", *public_classes]
