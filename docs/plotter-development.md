# Plotter development

This guide explains how to add custom plotters to `ssl_vista`.

## Choose a base class

## PyVista plotters

Inherit from `_BaseVisualPlotter` (or `BaseCanvasPlotter` if you want built-in robot/grid helpers).

Required methods:

- `setup_scene(self)`
- `reset_scene(self, sim_data, sim_settings)`
- `update_all_scene_objects(self, sim_data, idx)`

## Matplotlib plotters

Inherit from `BaseMplPlotter`.

Required methods:

- `init_artists(self, sim_data, sim_settings)`
- `update_artists(self, sim_data, idx)`

Also define `self.axes_config` in `__init__`.

## Minimal Matplotlib example

A working example is provided in:

- `src/ssl_vista/data/grid_layouts/mpl_example.py`
- `src/ssl_vista/data/grid_layouts/example_mpl.json`

The layout entry points to a module file and class:

```json
{
  "type": "BaseMplPlotter",
  "module_path": "mpl_example.py",
  "class_name": "PlotterMplExample"
}
```

## Registering built-in plotters

Built-ins are resolved through the plotter registry (`ssl_vista.plotters.registry`).
To make a new built-in available:

1. Add a class under `src/ssl_vista/plotters`.
2. Ensure it inherits from a valid base and exposes required methods.
3. Reference its class name in layout `type`.

The package `plotters/__init__.py` imports classes and registers concrete plotter types at import time.

For local custom plugins, use layout fields `module_path` and `class_name`; these are validated by schema and then loaded by the registry loader.

## Shared context and cross-plotter interaction

`SimulationGridContext` provides shared state/signals.
Current signal:

- `robot_focus_changed`

Use this to synchronize robot selection across plotters.

## Recommended implementation checklist

- Validate required keys/shapes in `reset_scene` or custom checks.
- Avoid expensive recomputation in per-frame updates.
- Keep state in instance attributes, not globals.
- Provide sane defaults for label names and style args.
- Document required data keys in docstring.

## Testing custom plotters

- Start with bundled sample data to verify base behavior.
- Exercise keyboard interactions if overridden.
- Confirm layout loading failures are explicit for bad config.
- Run `just test` and `just docs-build` before submitting changes.
