"""
SSL Simulator Vista - A PyVista/Matplotlib-based Visualization Tool for the SSL Simulator
"""
import inspect

# Configuration
from .config import CONFIG

# Plotters
from .plotters.pv_utils.scene_objects import *
from .plotters import * 

# Data
from .data import *

public_classes = []
modules = plotters

for name, obj in inspect.getmembers(plotters, inspect.isclass):
    if name.startswith("Base") or name.startswith("Plotter"):
        public_classes.append(name)

# Collect all __all__ from scene_objects.py
from .plotters.pv_utils import scene_objects
public_classes.extend(scene_objects.__all__)

# Define the public API
__all__ = ["CONFIG"] + public_classes
