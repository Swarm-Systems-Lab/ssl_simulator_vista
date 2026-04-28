__all__ = ["BaseMplPlotter"]

import logging

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtCore, QtGui
from ssl_simulator.logging import requires_log_level

from ._base_plotters import _BasePlotter
from ._protected_attrs_mixin import ProtectedAttrsMixin

_logger = logging.getLogger(__name__)


class BaseMplPlotter(ProtectedAttrsMixin, _BasePlotter):
    """
    Base class for Matplotlib-based plotters.

    Subclasses should:
        - define self.axes_config: dict specifying axes
            e.g., {"main": {"position":[x0,y0,dx,dy], "projection":"3d"}}
        - implement init_artists(self)
        - implement update_artists(self, frame_data)
    """

    # Attributes managed by the base class that should not be directly reassigned
    _PROTECTED_ATTRS = frozenset(
        ["axes", "artists", "line_configs", "_axes_config", "fig", "canvas"]
    )

    def __init__(self, parent=None, context=None, figsize=(8, 6), dpi=100):
        super().__init__()
        self.context = context

        self.artists = {}
        self.line_configs = {}

        self._axes_config = {}
        self._initialized = False

        self.figsize, self.dpi = figsize, dpi
        self.fig = plt.figure(figsize=figsize, dpi=dpi)
        self.axes = {}

        # Embed in Qt if parent provided
        self.canvas = FigureCanvas(self.fig)
        if parent:
            self.canvas.setParent(parent)
        self.set_widget(self.canvas)

    @property
    def axes_config(self):
        return self._axes_config

    @axes_config.setter
    def axes_config(self, value):
        if self._initialized:
            raise RuntimeError("Cannot modify axes_config after scene initialization.")
        self._axes_config.update(value)

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
    # HELPER METHODS
    # ---------------------------------------------------------------

    def register_lines(self, axis, var, name=None, shape=None, units="", extract=None, **kw_style):
        """
        Register a group of lines to be plotted and updated.
        Parameters:
            name: str, key for this group of lines
            axis: str, axis key in self.axes
            var: str, variable name in sim_data
            shape: int, number of lines (e.g. 3 for x/y/z)
            units: str, units for axis label
            extract: function or None, how to extract data from sim_data[var]
        """
        if name is None:
            base_name = f"{axis}_{var}_lines"
            name = base_name
            counter = 1
            while name in self.line_configs:
                name = f"{base_name}_{counter}"
                counter += 1
        self.line_configs[name] = {
            "axis": axis,
            "var": var,
            "shape": shape,
            "units": units,
            "extract": extract,
            "style": kw_style,
        }

    def _init_lines_from_config(self, sim_data):
        """
        Initialize all registered lines and set axis labels/limits.
        """
        for name, cfg in self.line_configs.items():
            ax = self.axes[cfg["axis"]]
            data = sim_data[cfg["var"]]
            if cfg["extract"]:
                data = cfg["extract"](data)
            if cfg["shape"] is None:
                cfg["shape"] = data.shape[1] if len(data.shape) > 1 else 1
            # Assume time axis is always present
            time = sim_data["time"]
            ax.set_xlim(time.min(), time.max())
            ax.set_ylim(data.min() * 1.1, data.max() * 1.1)
            ax.set_xlabel(r"$t$ [T]")
            ax.set_ylabel(f"{cfg['var']} [{cfg['units']}]")
            self.artists[name] = []
            for i in range(cfg["shape"]):
                style = {k: v[i] if isinstance(v, list) else v for k, v in cfg["style"].items()}
                (line,) = ax.plot([], [], **style)
                self.artists[name].append(line)
            ax.legend()

    def _update_lines(self, sim_data, idx):
        """
        Update all registered lines with new data.
        """
        time = sim_data["time"]
        for name, cfg in self.line_configs.items():
            data = sim_data[cfg["var"]]
            if cfg["extract"]:
                data = cfg["extract"](data)
            if len(self.artists[name]) > 1:
                for i, line in enumerate(self.artists[name]):
                    line.set_data(time[: idx + 1], data[: idx + 1, i])
            else:
                self.artists[name][0].set_data(time[: idx + 1], data[: idx + 1])

    # ---------------------------------------------------------------
    # SETUP/RESET/UPDATE SCENE
    # ---------------------------------------------------------------
    def setup_scene(self):
        """Create axes and initialize artists."""
        if not self._initialized:
            self._setup_axes()
            self._initialized = True
            self.fig.canvas.draw_count = 0  # reset draw count
            _logger.debug(f"Scene setup complete. Axes: {list(self.axes.keys())}")

    def reset_scene(self, sim_data, sim_settings):
        """Reset the scene to its initial state."""
        for ax in self.axes.values():  # clear axes but keep them
            ax.cla()
            ax.grid(True)

        self._init_lines_from_config(sim_data)
        self.init_artists(sim_data, sim_settings)
        self.fig.canvas.draw_count = 0  # reset draw count

    def update_all_scene_objects(self, sim_data, idx):
        """Update all artists in the scene."""
        self._update_lines(sim_data, idx)
        self.update_artists(sim_data, idx)
        self.canvas.draw_idle()

    # ---------------------------------------------------------------
    # SETUP/UPDATE AXES
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
            _logger.debug(f"Created axis '{key}' with rect={rect} and config={cfg_copy}")

    def _update_axes(self, shift=None, scale_factor=1.0):
        """Update axes positions for panning and zooming."""
        if shift is None:
            shift = [0, 0]
        dx, dy = shift
        for key, _cfg in self.axes_config.items():
            ax = self.axes[key]
            pos = ax.get_position().bounds
            new_pos = [pos[0] + dx, pos[1] + dy, pos[2] * scale_factor, pos[3] * scale_factor]
            ax.set_position(new_pos)
        self.fig.canvas.draw_idle()

    def _print_position_axes(self):
        """Log current axes positions for debugging."""
        for key, ax in self.axes.items():
            bounds = ax.get_position().bounds
            _logger.debug(f"Axis '{key}' position: {bounds}")

    # ---------------------------------------------------------------
    # KEY EVENT HANDLING
    # ---------------------------------------------------------------
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == QtCore.Qt.Key_Plus:
            self._update_axes(scale_factor=1.05)
        elif event.key() == QtCore.Qt.Key_Minus:
            self._update_axes(scale_factor=1 / 1.05)
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
    def collect_scene_objects(self, verbose: bool = False) -> dict:
        """Return a structured snapshot of this plotter's matplotlib artists.

        Pure data — no logging side effects.
        """
        line_configs = {
            name: {"axis": cfg["axis"], "var": cfg["var"], "shape": cfg["shape"]}
            for name, cfg in self.line_configs.items()
        }

        artists = {name: len(artist_list) for name, artist_list in self.artists.items()}

        axes = {key: len(ax.get_children()) for key, ax in self.axes.items()}

        return {
            "plotter": self.__class__.__name__,
            "line_configs": line_configs,
            "artists": artists,
            "axes": axes,
        }
