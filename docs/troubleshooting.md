# Troubleshooting

This page captures common issues when running `ssl_vista` locally.

## GUI does not open on Linux

Symptoms:

- App exits immediately or prints Qt platform plugin errors
- Messages related to xcb/Wayland/OpenGL initialization

What to check:

1. Run from a graphical session (not a headless shell).
2. Ensure X11/xcb support is available in your environment.
3. Confirm Qt and VTK dependencies are installed correctly.

The app sets `QT_QPA_PLATFORM=xcb` for Linux compatibility in `MainWindow`.

Note that this is set **at import time**, so it overrides any value you export in the shell. Running
the Qt app fully headless (`QT_QPA_PLATFORM=offscreen`) therefore does not work without patching
that line. To exercise scene-object logic without a display, drive the PyVista objects directly
against an off-screen `pv.Plotter(off_screen=True)` instead of launching the app.

## `FileNotFoundError` for layout or sample

If `--layout` or `--data-path` fails:

- For bundled assets, pass the **name without extension** (for example `2d_canvas`, `data_uny_test`).
- For custom files, pass a valid path (`./my_layout.json`, `./run.csv`).

Useful checks:

```bash
uv run sslvista --list-layouts
uv run sslvista --list-data
```

## Layout validation errors

Symptoms:

- Error indicating invalid layout schema before the app window appears

Cause:

- Layout JSON failed strict schema checks (invalid shape, duplicate/out-of-bounds positions, unsupported fields, or missing custom loader fields).

Fix:

1. Validate top-level fields: `shape`, `plotters`.
2. Ensure each plotter has a unique valid `position`.
3. For custom local plotters, provide both `module_path` and `class_name`.
4. Remove unknown fields from layout entries.

## Data file loads but plotter fails

Symptoms:

- Runtime `ValueError` about missing keys or shape mismatch

Cause:

- Plotters validate required keys and array dimensions (for example `p`, `theta`, `R`). Lookup is by
  **exact key**, and `ssl_simulator` logs flat names - a run logging `p` will not match a plotter
  configured for `robot.p`.

Fix:

1. Verify your CSV produces expected arrays through `ssl_simulator.load_sim`.
2. Compare with bundled sample files.
3. Match plotter labels in layout `args` to available data keys.

See [Data schema](data-schema.md).

## `ModuleNotFoundError` importing `ssl_vista.mpl`

Symptoms:

- `ssl_vista.mpl requires Matplotlib and SciPy. Install the optional extra: pip install ssl_vista[mpl]`

Cause:

- Matplotlib and SciPy are **optional**. 2-D plotting is expected to move to a GPU-backed stack, so
  Matplotlib is deliberately not a hard dependency.

Fix:

```bash
pip install "ssl_vista[mpl]"   # or: uv add "ssl_vista[mpl]"
```

Matplotlib-based plotters under `plotters/` are skipped silently when the extra is absent, so a
layout that uses one will report the plotter type as unknown rather than an import error.

## Custom Matplotlib plotter fails to load

Symptoms:

- Error about missing `module_path` / `class_name`
- Import/class loading exceptions

Checklist:

1. In layout JSON, `type` should use a Base* dynamic entry and include `module_path` and `class_name`.
2. `module_path` must be relative to the layout JSON file or an absolute existing path.
3. The class must inherit from `BaseMplPlotter` and implement required methods.

See [Layout schema](layout-schema.md) and [Plotter development](plotter-development.md).

## Keyboard shortcuts do not respond

If shortcuts appear ignored:

- Click inside the main window once to ensure focus.
- If interacting inside embedded widgets (PyVista/Matplotlib), focus may shift.
- Use toolbar controls as a fallback for playback and frame stepping.

## Local checks for contributors

Before opening a PR, run:

```bash
just lint
just test
just typecheck
just docs-build
just validate-docs
```

## Still stuck?

- Open an issue with:
	- command used
	- full traceback
	- layout file
	- data source information
	- OS and Python version
