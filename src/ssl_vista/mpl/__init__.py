"""Matplotlib visualization utilities (optional).

Small, reusable Matplotlib helpers - publication styling, 2-D robot glyphs, vector/axis drawing,
colormaps, and animation updaters - shared across the simulation ecosystem. They are pure
Matplotlib (no Qt), so they import without a display.

This is an **optional** feature: install the ``mpl`` extra (``pip install ssl_vista[mpl]``) to pull
Matplotlib + SciPy. 2-D plotting will eventually move to a GPU-backed stack (e.g. pyqtgraph), so
Matplotlib is deliberately not a hard dependency of ssl_vista.
"""

try:
    import matplotlib
    import scipy
except ModuleNotFoundError as exc:  # pragma: no cover - guidance for a missing optional dep
    raise ModuleNotFoundError(
        "ssl_vista.mpl requires Matplotlib and SciPy. Install the optional extra: "
        "`pip install ssl_vista[mpl]` (or `uv add ssl_vista[mpl]`)."
    ) from exc

from .basics import (
    alpha_cmap,
    config_axis,
    config_data_axis,
    get_nice_ticks,
    smooth_interpolation,
    vector2d,
    zoom_range,
)
from .figure_tools import initialize_plot, save_paper_figure, set_paper_parameters
from .patches import fixedwing_patch, unicycle_patch

__all__ = [
    "alpha_cmap",
    "config_axis",
    "config_data_axis",
    "fixedwing_patch",
    "get_nice_ticks",
    "initialize_plot",
    "save_paper_figure",
    "set_paper_parameters",
    "smooth_interpolation",
    "unicycle_patch",
    "vector2d",
    "zoom_range",
]
