__all__ = ["BaseMplPlotter"]

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtCore, QtGui

from ssl_vista import CONFIG
from ._base_plotters import _BasePlotter

class BaseMplPlotter(_BasePlotter):
    """
    Base class for Matplotlib-based plotters.
    
    Subclasses should:
        - define self.axes_config: dict specifying axes
        - implement init_artists(self)
        - implement update_artists(self, frame_data)
        - override compute_frame(self, frame_idx) if needed for large logs
    """

    def __init__(self, parent=None, context=None, figsize=(8,6), dpi=100):
        self.context = context
        
        # -- To be defined by subclass !!
        # e.g., {"main": {"position":[x0,y0,dx,dy], "projection":"3d"}}
        self.axes_config = {} 
        # ----------------------------

        self.figsize, self.dpi = figsize, dpi
        self.fig = plt.figure(figsize=figsize, dpi=dpi)
        self.axes = {}
        self._initialized = False

        # Embed in Qt if parent provided
        self.canvas = FigureCanvas(self.fig)
        if parent:
            self.canvas.setParent(parent)
        self.set_widget(self.canvas)

    def setup_scene(self):
        """Create axes and initialize artists."""
        if not self._initialized:
            self._setup_axes()
            self._initialized = True
            self.fig.canvas.draw_count = 0  # reset draw count

            if CONFIG["DEBUG"]:
                print(f"[DEBUG] Scene setup complete.\n")

    def reset_scene(self, sim_data, sim_settings):
        """Reset the scene to its initial state."""
        # Clear all artists from the axes
        for ax in self.axes.values():
            ax.cla()

        # Reinitialize artists
        self.init_artists(sim_data, sim_settings)
        self.fig.canvas.draw_count = 0  # reset draw count

        if CONFIG["DEBUG"]:
            self._debug_artists()

    def update_all_scene_objects(self, sim_data, idx):
        """Update all artists in the scene."""
        self.update_artists(sim_data, idx)
    
    # ---------------------------------------------------------------
    # ABSTRACT METHODS (must be implemented)
    # ---------------------------------------------------------------
    def init_artists(self, sim_data, sim_settings):
        """Initialize all plot elements. Must be implemented by subclass."""
        raise NotImplementedError
    
    def update_artists(self, sim_data, idx):
        """Update plot elements for a new frame. Must be implemented by subclass."""
        raise NotImplementedError
    
    # ---------------------------------------------------------------
    # AXES SETUP AND UPDATE
    # ---------------------------------------------------------------
    def _setup_axes(self):
        """Create axes based on self.axes_config."""
        for key, cfg in self.axes_config.items():
            cfg_copy = cfg.copy()  # avoid modifying the original config

            # Extract rect/position
            rect = None
            if "position" in cfg_copy:
                rect = cfg_copy.pop("position")
            if "rect" in cfg_copy:
                if rect is not None:
                    raise ValueError(f"Axis '{key}': Cannot provide both 'rect' and 'position'.")
                rect = cfg_copy.pop("rect")
            if rect is None:
                raise ValueError(f"Axis '{key}': Must provide either 'position' or 'rect'.")

            # Create axis with remaining kwargs (e.g., projection)
            self.axes[key] = self.fig.add_axes(rect, **cfg_copy)

            if CONFIG.get("DEBUG", False):
                print(f"[DEBUG] Created axis '{key}' with rect={rect} and kwargs={cfg_copy}")
    
    def _update_axes(self, shift=[0,0], scale_factor=1.0):
        """Update axes positions for panning and zooming."""
        dx, dy = shift
        for key, cfg in self.axes_config.items():
            ax = self.axes[key]
            pos = ax.get_position().bounds
            new_pos = [pos[0]+dx, pos[1]+dy, pos[2]*scale_factor, pos[3]*scale_factor]
            ax.set_position(new_pos)
        self.fig.canvas.draw_idle()

    def _print_position_axes(self):
        """Print current axes positions for debugging."""
        print("\nCurrent Axes Positions -----")
        for key, ax in self.axes.items():
            pos = ax.get_position().bounds
            print(f"Axis '{key}': position={np.round(pos, 4)}")
        print("-" * (len("Current Axes Positions -----") + 4))

    # ---------------------------------------------------------------
    # KEY EVENT HANDLING
    # ---------------------------------------------------------------
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == QtCore.Qt.Key_Plus:
            self._update_axes(scale_factor=1.05)
        elif event.key() == QtCore.Qt.Key_Minus:
            self._update_axes(scale_factor=1/1.05)
        elif event.key() == QtCore.Qt.Key_Left:
            self._update_axes(shift=[-0.01, 0])
        elif event.key() == QtCore.Qt.Key_Right:
            self._update_axes(shift=[0.01, 0])
        elif event.key() == QtCore.Qt.Key_Up:
            self._update_axes(shift=[0, 0.01])
        elif event.key() == QtCore.Qt.Key_Down:
            self._update_axes(shift=[0, -0.01])
        elif event.key() == QtCore.Qt.Key_I:
            self._print_position_axes()
        
        event.accept()  # prevent further processing

    # ---------------------------------------------------------------
    # DEBUG UTILITIES
    # ---------------------------------------------------------------

    def _debug_artists(self):
        """
        Print all artists in each axis with their key and type.
        Useful to inspect plot elements during development.
        """
        
        print("\n[DEBUG] BaseMplPlotter Artists Debug -----")
        total_count = 0

        def count_and_print(artist, prefix=""):
            """Recursively print and count artists."""
            nonlocal total_count
            if isinstance(artist, dict):
                for k, v in artist.items():
                    count_and_print(v, prefix=f"{prefix}[{k}]")
            elif isinstance(artist, list):
                for i, a in enumerate(artist):
                    count_and_print(a, prefix=f"{prefix}[{i}]")
            elif isinstance(artist, np.ndarray):
                print(f"{prefix} np.ndarray shape={artist.shape}, dtype={type(artist.flat[0]).__name__}")
                total_count += artist.size
            else:
                print(f"{prefix} {type(artist).__name__}: {artist}")
                total_count += 1

        for ax_key, ax in self.axes.items():
            print(f"Axis '{ax_key}' ({type(ax).__name__}):")
            group = ax.get_children()
            if not group:
                print(f"    [!] No artists in axis '{ax_key}'")
                continue
            count_and_print(group, prefix="    ")

        print(f"Total artists: {total_count}")
        print("-" * (len("[DEBUG] BaseMplPlotter Artists Debug -----") + 4))
