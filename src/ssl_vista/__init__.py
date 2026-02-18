"""
SSL Simulator Vista - A PyVista/Matplotlib-based Visualization Tool for the SSL Simulator
"""

# Only expose CONFIG at the top level to avoid circular imports
from .config import CONFIG

__all__ = ["CONFIG"]
