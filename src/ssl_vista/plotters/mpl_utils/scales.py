"""Axis **scales** and tick **formats** - two different things, kept apart.

**Scale** is the axis *transform*: how data coordinates map to display coordinates. It changes the
geometry of the axis and therefore which limits are legal - a ``log`` axis cannot show values
``<= 0``. These are matplotlib's own (``linear``, ``log``, ``symlog``, ``asinh``, ``logit``, ...).

**Format** is the *labelling*: where ticks are placed (Locator) and what text they carry
(Formatter). It moves no data and leaves the transform alone.

They are separate config keys (``yscale`` vs ``yformat``) precisely so they compose: a log axis with
percentage labels, or radian ticks on a symlog axis, are both expressible.
"""

import logging

import numpy as np
from matplotlib.ticker import FuncFormatter, MultipleLocator

_logger = logging.getLogger(__name__)

__all__ = ["apply_format", "apply_scale", "available_formats", "available_scales"]


def _axis_of(ax, axis: str):
    if axis not in ("x", "y"):
        raise ValueError(f"axis must be 'x' or 'y', got {axis!r}.")
    return ax.xaxis if axis == "x" else ax.yaxis


# ---------- tick format handlers (labelling only; the transform is untouched) ----------


def _format_radians(ax, axis: str) -> None:
    """Place ticks every π/2 and label them as multiples of π."""
    target = _axis_of(ax, axis)

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


def _format_degrees(ax, axis: str) -> None:
    """Label ticks in degrees (the underlying data stays in radians)."""
    _axis_of(ax, axis).set_major_formatter(FuncFormatter(lambda v, _p: f"{np.degrees(v):.0f}°"))


def _format_percent(ax, axis: str) -> None:
    """Label a 0-1 fraction as a percentage."""
    _axis_of(ax, axis).set_major_formatter(FuncFormatter(lambda v, _p: f"{100 * v:.0f}%"))


# ---------- registries and dispatchers ----------


_FORMATS = {
    "radians": _format_radians,
    "degrees": _format_degrees,
    "percent": _format_percent,
}


def available_scales() -> list[str]:
    """Matplotlib's axis transforms (the valid ``xscale``/``yscale`` values)."""
    import matplotlib.scale

    return sorted(matplotlib.scale.get_scale_names())


def available_formats() -> list[str]:
    """The tick-format presets (the valid ``xformat``/``yformat`` values)."""
    return sorted(_FORMATS)


def apply_scale(ax, axis: str, scale: str) -> None:
    """Set the axis **transform** on ``ax``'s x or y axis.

    Raises on an unknown name, listing the valid ones - matplotlib alone would fail deeper down
    with no reference to which axis was misconfigured. Tick formats belong to :func:`apply_format`.
    """
    _axis_of(ax, axis)  # validates `axis`

    valid = available_scales()
    if scale not in valid:
        hint = ""
        if scale in _FORMATS:
            hint = f" - '{scale}' is a tick format, use '{axis}format' instead of '{axis}scale'"
        raise ValueError(f"unknown scale {scale!r}; expected one of {', '.join(valid)}{hint}.")

    setter = ax.set_xscale if axis == "x" else ax.set_yscale
    setter(scale)


def apply_format(ax, axis: str, fmt: str) -> None:
    """Apply a tick **format** preset to ``ax``'s x or y axis (labels/locators only)."""
    _axis_of(ax, axis)  # validates `axis`

    if fmt not in _FORMATS:
        hint = ""
        if fmt in available_scales():
            hint = f" - '{fmt}' is an axis scale, use '{axis}scale' instead of '{axis}format'"
        raise ValueError(
            f"unknown tick format {fmt!r}; expected one of {', '.join(available_formats())}{hint}."
        )
    _FORMATS[fmt](ax, axis)
