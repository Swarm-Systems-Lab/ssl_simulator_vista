import importlib
import pkgutil
import inspect

# Automatically import all modules inside the "plotters" package
__all__ = []

for module_info in pkgutil.iter_modules(__path__):
    module_name = module_info.name
    full_module_name = f"{__name__}.{module_name}"
    module = importlib.import_module(full_module_name)

    # Find all classes inside the module that look like plotters
    for name, obj in inspect.getmembers(module, inspect.isclass):
        # Ensure it's defined in this module (not an imported one)
        if obj.__module__ == full_module_name:
            globals()[name] = obj
            __all__.append(name)