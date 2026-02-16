from __future__ import annotations

from pathlib import Path

from ssl_simulator import load_class_from_file

from ._base_plotters import _BasePlotter

_REGISTRY: dict[str, type[_BasePlotter]] = {}


def register_plotter(name: str, plotter_cls: type[_BasePlotter], overwrite: bool = False) -> None:
    """Register a plotter class by name."""
    if not issubclass(plotter_cls, _BasePlotter):
        raise TypeError(f"Plotter '{name}' must inherit from _BasePlotter.")

    if not overwrite and name in _REGISTRY:
        raise ValueError(f"Plotter '{name}' is already registered.")

    _REGISTRY[name] = plotter_cls


def get_plotter_class(name: str) -> type[_BasePlotter]:
    """Get a registered plotter class by name."""
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown plotter type '{name}'. Registered plotters: [{available}]")
    return _REGISTRY[name]


def list_registered_plotters() -> list[str]:
    """Return all registered plotter names."""
    return sorted(_REGISTRY)


def create_plotter_instance(
    plotter_type: str,
    *,
    context=None,
    module_path: str | None = None,
    class_name: str | None = None,
    base_dir: Path | None = None,
    **kwargs,
) -> _BasePlotter:
    """Create a plotter instance from registry or from a local file plugin."""
    if module_path is not None and class_name is not None:
        module_file = Path(module_path)
        if not module_file.is_absolute():
            if base_dir is None:
                raise ValueError("base_dir is required when module_path is relative.")
            module_file = (base_dir / module_file).resolve()

        plotter_cls = load_class_from_file(str(module_file), class_name)
        if not issubclass(plotter_cls, _BasePlotter):
            raise TypeError(
                f"Class '{class_name}' from '{module_file}' must inherit from _BasePlotter."
            )
        return plotter_cls(context=context, **kwargs)

    plotter_cls = get_plotter_class(plotter_type)
    return plotter_cls(context=context, **kwargs)
