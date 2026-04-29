import logging

import numpy as np
from matplotlib.ticker import FuncFormatter, MultipleLocator

_logger = logging.getLogger(__name__)

# ---------- custom scale handlers ----------


def _apply_radian_scale(ax, axis: str) -> None:
    """Format ticks as multiples of π. axis is 'x' or 'y'."""
    target = ax.xaxis if axis == "x" else ax.yaxis

    def _fmt(val, _pos):
        if val == 0:
            return "0"
        frac = val / np.pi
        # Snap near-integer multiples to clean labels
        if abs(frac - round(frac)) < 1e-6:
            n = round(frac)
            if n == 1:
                return r"$\pi$"
            if n == -1:
                return r"$-\pi$"
            return rf"${n}\pi$"
        # Half-multiples
        if abs(2 * frac - round(2 * frac)) < 1e-6:
            n = round(2 * frac)
            sign = "-" if n < 0 else ""
            n_abs = abs(n)
            if n_abs == 1:
                return rf"${sign}\pi/2$"
            return rf"${sign}{n_abs}\pi/2$"
        return f"{val:.2f}"

    target.set_major_locator(MultipleLocator(np.pi / 2))
    target.set_major_formatter(FuncFormatter(_fmt))


def _apply_degree_scale(ax, axis: str) -> None:
    """Format ticks as degree values (assumes data is in radians)."""
    target = ax.xaxis if axis == "x" else ax.yaxis
    target.set_major_formatter(FuncFormatter(lambda v, _p: f"{np.degrees(v):.0f}°"))


# ---------- scale registry and dispatcher ----------


# Registry: name -> handler.
_CUSTOM_SCALES = {
    "radians": _apply_radian_scale,
    "degrees": _apply_degree_scale,
}


def apply_scale(ax, axis: str, scale: str) -> None:
    """Apply a scale to ax's x or y axis. Dispatches custom scales by name."""
    if scale in _CUSTOM_SCALES:
        _CUSTOM_SCALES[scale](ax, axis)
    else:
        # Defer to matplotlib's built-in scales
        setter = ax.set_xscale if axis == "x" else ax.set_yscale
        setter(scale)
