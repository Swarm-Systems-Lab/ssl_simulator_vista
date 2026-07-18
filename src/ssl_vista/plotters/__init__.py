import importlib
import inspect
import logging
import pkgutil

from ._base_plotters import _BasePlotter
from .registry import (
    create_plotter_instance,
    get_plotter_class,
    list_registered_plotters,
    register_plotter,
)

_logger = logging.getLogger(__name__)

# Automatically import all modules inside the "plotters" package
__all__ = []

for module_info in pkgutil.iter_modules(__path__):
    module_name = module_info.name
    full_module_name = f"{__name__}.{module_name}"
    try:
        module = importlib.import_module(full_module_name)
    except ImportError as exc:
        # Optional backend not installed (e.g. the Matplotlib plotters need the `mpl` extra).
        # Skip it so the rest of the registry still loads.
        _logger.debug("skipping plotter module %s: %s", full_module_name, exc)
        continue

    # Find all classes inside the module that look like plotters
    for name, obj in inspect.getmembers(module, inspect.isclass):
        # Ensure it's defined in this module (not an imported one)
        if obj.__module__ == full_module_name:
            globals()[name] = obj
            __all__.append(name)

            if not name.startswith("_") and issubclass(obj, _BasePlotter):
                register_plotter(name, obj, overwrite=True)

__all__.extend(
    [
        "create_plotter_instance",
        "get_plotter_class",
        "list_registered_plotters",
        "register_plotter",
    ]
)
