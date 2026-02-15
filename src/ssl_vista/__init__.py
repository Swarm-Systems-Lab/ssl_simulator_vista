"""
SSL Simulator Vista - A PyVista/Matplotlib-based Visualization Tool for the SSL Simulator
"""

__version__ = "0.0.2"

# Only expose CONFIG at the top level to avoid circular imports
from .config import CONFIG

__all__ = ["CONFIG"]
