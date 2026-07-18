__all__ = ["BaseMplPlotter"]

import logging

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtCore, QtGui

from ssl_vista.plotters.mpl_utils.scales import apply_scale

from ._base_plotters import _BasePlotter
from ._protected_attrs_mixin import ProtectedAttrsMixin

_logger = logging.getLogger(__name__)


def _expand_limits(current, new_min, new_max, pad_frac=0.05, min_pad=1e-6):
    """Return limits that cover ``current`` and ``[new_min, new_max]``.

    ``current`` is either None (no prior limits) or a (lo, hi) tuple. Padding
    is applied as a fraction of the data range, with ``min_pad`` as a floor
    so flat data still gets a visible window.
    """
    span = max(new_max - new_min, min_pad)
    pad = span * pad_frac
    lo, hi = new_min - pad, new_max + pad
    if current is not None:
        cur_lo, cur_hi = current
        lo = min(lo, cur_lo)
        hi = max(hi, cur_hi)
    return lo, hi


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
    # API METHODS
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

    # ---------------------------------------------------------------
    # HELPER METHODS
    # ---------------------------------------------------------------
    def _init_lines_from_config(self, sim_data):
        """Initialize all registered lines and set axis labels/limits.

        When multiple line groups share an axis, y-limits accumulate so every
        line stays in view. x-limits use the time vector and are uniform.
        """
        time = sim_data["time"]
        t_min, t_max = float(time.min()), float(time.max())

        # Track which axes we've already touched in this call so we know whether
        # to seed limits or expand them. ax.get_ylim() can't tell us "untouched"
        # because matplotlib seeds defaults eagerly.
        seen_axes: set[str] = set()

        for name, cfg in self.line_configs.items():
            ax = self.axes[cfg["axis"]]
            data = sim_data[cfg["var"]]
            if cfg["extract"]:
                data = cfg["extract"](data)
            if cfg["shape"] is None:
                cfg["shape"] = data.shape[1] if len(data.shape) > 1 else 1

            d_min, d_max = float(data.min()), float(data.max())

            if cfg["axis"] not in seen_axes:
                ax.set_xlim(t_min, t_max)
                y_lo, y_hi = _expand_limits(None, d_min, d_max)
                ax.set_xlabel(r"$t$ [T]")
                ax.set_ylabel(f"{cfg['var']} [{cfg['units']}]")
                seen_axes.add(cfg["axis"])
            else:
                y_lo, y_hi = _expand_limits(ax.get_ylim(), d_min, d_max)
                # Append to ylabel so multi-variable axes are self-documenting
                existing_label = ax.get_ylabel()
                new_label = f"{cfg['var']} [{cfg['units']}]"
                if new_label not in existing_label:
                    ax.set_ylabel(f"{existing_label}, {new_label}")

            ax.set_ylim(y_lo, y_hi)

            self.artists[name] = []
            for i in range(cfg["shape"]):
                style = {k: v[i] if isinstance(v, list) else v for k, v in cfg["style"].items()}
                (line,) = ax.plot([], [], **style)
                self.artists[name].append(line)
            ax.legend()

            _logger.debug_verbose(
                "axis limits configured",
                extra={
                    "axis": cfg["axis"],
                    "line_group": name,
                    "xlim": [t_min, t_max],
                    "ylim": [y_lo, y_hi],
                    "data_range": [d_min, d_max],
                },
            )

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

    def _reapply_scales(self):
        """(Re-)apply xscale/yscale from axes_config to all axes.

        Needed after ax.cla(), which resets locators/formatters.
        """
        for key, cfg in self.axes_config.items():
            ax = self.axes[key]
            xscale = cfg.get("xscale")
            yscale = cfg.get("yscale")
            if xscale:
                apply_scale(ax, "x", xscale)
            if yscale:
                apply_scale(ax, "y", yscale)

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

        # cla() resets locators/formatters; re-apply axis scales.
        self._reapply_scales()

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
            cfg_copy = cfg.copy()

            rect = cfg_copy.pop("position", None) or cfg_copy.pop("rect", None)
            if rect is None:
                raise ValueError(f"Axis '{key}': must provide 'position' or 'rect'.")

            # Strip scale specs; they're handled by _reapply_scales.
            cfg_copy.pop("xscale", None)
            cfg_copy.pop("yscale", None)

            self.axes[key] = self.fig.add_axes(rect, **cfg_copy)

        self._reapply_scales()

        _logger.debug_verbose(
            "axes created",
            extra={
                "axes": list(self.axes.keys()),
                "scales": {
                    k: {"xscale": v.get("xscale"), "yscale": v.get("yscale")}
                    for k, v in self.axes_config.items()
                },
            },
        )

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

    def _collect_position_axes(self):
        """Log current axes positions at DEBUG level."""
        return {key: list(ax.get_position().bounds) for key, ax in self.axes.items()}

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
            _logger.debug(
                f"{self.__class__.__name__} axes",
                extra={"positions": self._collect_position_axes()},
            )

        event.accept()  # prevent further processing

    # ---------------------------------------------------------------
    # DEBUG UTILITIES
    # ---------------------------------------------------------------
    def collect_scene_objects(self, verbose: bool = False) -> dict:
        """Return a structured snapshot of this plotter's matplotlib artists.

        Pure data - no logging side effects.
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
